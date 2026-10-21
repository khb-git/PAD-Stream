#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F1-R2"

PROTOCOL_ID = (
    "POSTV16_AV4_F1_R2_CORRECTED_RESTART_STATE_REPRESENTATION_AND_"
    "CONSERVATIVE_PARENT_STATE_GRID_TO_REFRESHED_STREAMLINE_"
    "PROJECTION_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F1R2_F1R1_TECHNICAL_CLOSURE_BOUND_E1R2_STRUCTURAL_RESTART_"
    "INCOMPATIBILITY_BOUND_RESTART_STATE_REPRESENTATION_CONSERVATIVE_"
    "SPLIT_PARENT_PROJECTION_AND_TEMPORAL_SEMANTICS_PROSPECTIVELY_"
    "FROZEN_NO_PROJECTION_EXECUTION"
)

STATUS_BLOCKED = "AV4F1R2_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_F1R1_COMMIT = "7265c6cfaf736aa3e662a3e3f8cf7704fadc9b0c"

CONTROL_REALIZATION = "AV3CR0003"
CONTROL_POROSITY = "AV2PHI0003"
PARENT_DAY = 365.0
FIRST_CANDIDATE_TARGET_DAY = 500.0
FIRST_CANDIDATE_DELTA_DAY = 135.0

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200

# --------------------------------------------------------------------------------------------------
# Exact repository source authorities.
# --------------------------------------------------------------------------------------------------

F1_ORIGINAL = (
    "PAD_Stream_POSTV16_AV4_F1_Restart_State_and_"
    "Conservative_Parent_Projection_Freeze.py"
)
F1_ORIGINAL_BLOB = "556641cc8bfa7eac396cc082f08c35cc871c3836"

F1R1 = (
    "PAD_Stream_POSTV16_AV4_F1_R1_"
    "Technical_Source_Blob_Authority_Typo_Closure.py"
)
F1R1_BLOB = "671c95bbc3704238c4059a6cf5bcae5267e8acb7"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

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
    F1_ORIGINAL: F1_ORIGINAL_BLOB,
    F1R1: F1R1_BLOB,
    E1R2: E1R2_BLOB,
    A2E: A2E_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    R7R7D: R7R7D_BLOB,
    R7R7E: R7R7E_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F1R1_REL = BASE_AV4 / "POSTV16_AV4_F1_R1_Technical_Source_Blob_Authority_Typo_Closure"
F1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F1_R1_Summary.json"
F1R1_CORRECTION = "POSTV16_AV4_F1_R1_Corrected_Source_Blob_Authority_Contract.json"
F1R1_HANDOFF = "POSTV16_AV4_F1_R1_F1R2_Handoff_Contract.json"
F1R1_DECISION = "POSTV16_AV4_F1_R1_Decision_Contract.json"
F1R1_MANIFEST = "POSTV16_AV4_F1_R1_Artifact_Manifest.csv"
F1R1_STATUS = (
    "AV4F1R1_ORIGINAL_F1_TECHNICAL_BLOCK_PRESERVED_E1R2_BLOB_LITERAL_"
    "TYPO_ROOT_CAUSE_CLOSED_ALL_OTHER_SOURCE_BLOBS_REVALIDATED_"
    "CORRECTED_F1R2_CONTINUATION_AUTHORIZED_NO_F1_SCIENTIFIC_EXECUTION"
)

E1R2_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_A3_E1_R2_Summary.json"
E1R2_CLASSIFICATION = (
    "POSTV16_AV4_A3_E1_R2_Structural_Restart_Compatibility_Classification.json"
)
E1R2_DECISION = "POSTV16_AV4_A3_E1_R2_Decision_Contract.json"
E1R2_MANIFEST = "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv"
E1R2_STATUS = (
    "AV4A3E1R2_FULLY_SCHEMA_CORRECTED_REFRESHED_DAY365_X13_"
    "RECONSTRUCTION_INPUT_DOMAIN_AUDIT_PASS_REPRESENTATION_ONLY_"
    "STRUCTURAL_RESTART_INCOMPATIBILITY_NO_CHECKPOINT_INFERENCE"
)

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

BASE_AV1 = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
R7R7D_REL = BASE_AV1 / "POSTV16_AV1_D_R7_R7D_Horizontal_Face_Halo_Occupancy_Domain_Freeze"
R7R7D_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7D_Summary.json"
R7R7D_PROTOCOL = "POSTV16_AV1_D_R7_R7D_Frozen_Occupancy_Domain_Extension_Protocol.json"
R7R7D_MANIFEST = "POSTV16_AV1_D_R7_R7D_Artifact_Manifest.csv"
R7R7D_STATUS = (
    "AV1DR7R7D_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_DOMAIN_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
R7R7D_PROTOCOL_ID = (
    "POSTV16_AV1_D_R7_R7D_SINGLE_RING_HORIZONTAL_FACE_HALO_OCCUPANCY_EXTENSION_V1"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F1_R2_Restart_State_and_Conservative_Parent_Projection_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F1_R2_BLOCKED"


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


def self_test() -> None:
    # Tiny normalized-transpose conservation test.
    # Cell A has 12 kg and two subsegments with PV weights 1 and 3.
    # Cell B has 8 kg and one subsegment with PV weight 2.
    parent = {"A": 12.0, "B": 8.0}
    sub = [
        ("A", 0, 1.0),
        ("A", 1, 3.0),
        ("B", 1, 2.0),
    ]

    denom = {}
    for cell, _cv, pv in sub:
        denom[cell] = denom.get(cell, 0.0) + pv

    cv_mass = [0.0, 0.0]
    for cell, cv, pv in sub:
        cv_mass[cv] += parent[cell] * pv / denom[cell]

    assert abs(sum(cv_mass) - sum(parent.values())) < 1.0e-14
    assert abs(cv_mass[0] - 3.0) < 1.0e-14
    assert abs(cv_mass[1] - 17.0) < 1.0e-14

    # A non-support cell must remain residual, not be reverse-moved.
    residual = 5.0
    assert abs(sum(cv_mass) + residual - 25.0) < 1.0e-14

    assert FIRST_CANDIDATE_TARGET_DAY - PARENT_DAY == FIRST_CANDIDATE_DELTA_DAY

    print(
        "POSTV16-AV4-F1-R2 corrected restart-state / conservative "
        "parent-projection protocol self-test: PASS"
    )


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
        "POSTV16-AV4-F1-R2 — CORRECTED RESTART-STATE REPRESENTATION + CONSERVATIVE "
        "PARENT-STATE GRID→REFRESHED-STREAMLINE PROJECTION PROTOCOL FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO GRID→STREAMLINE PROJECTION EXECUTION. NO CV MASS INVERSION EXECUTION.")
    print("NO TEACHER. NO CHECKPOINT LOAD/INFERENCE. NO TRAINING.")
    print("NO PHYSICAL-TIME ADVANCE. NO MAPBACK. NO CMG.")
    print("HALO / OFF-STREAMLINE MASS IS NOT REVERSE-MOVED ONTO THE STREAMLINE SKELETON.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_F1R1_commit",
            parent == PARENT_F1R1_COMMIT,
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
        # Bind formal F1-R1 technical closure / corrected F1-R2 authority.
        # ------------------------------------------------------------------------------------------
        stage = "F1R1_closure_binding"

        r1 = drive / F1R1_REL
        gate("F1R1_output_present", r1.is_dir(), str(r1))
        mr1 = verify_manifest(r1, F1R1_MANIFEST)
        gate("F1R1_manifest_exact_6", len(mr1) == 6, len(mr1))

        sr1 = load_json(r1 / F1R1_SUMMARY)
        cr1 = load_json(r1 / F1R1_CORRECTION)
        hr1 = load_json(r1 / F1R1_HANDOFF)
        dr1 = load_json(r1 / F1R1_DECISION)

        gate("F1R1_status_exact", sr1["status"] == F1R1_STATUS, sr1["status"])
        gate(
            "F1R1_root_cause_exact",
            dr1["root_cause_closed"] is True
            and dr1["root_cause_type"] == "TECHNICAL_SOURCE_BLOB_LITERAL_TYPO"
            and cr1["bad_literal"] == "058f00fd12bd491dc7d7e471af3d4ff865af70"
            and cr1["correct_literal"] == E1R2_BLOB
            and cr1["bad_literal_length"] == 38
            and cr1["correct_literal_length"] == 40,
        )
        gate(
            "F1R1_original_F1_scientific_execution_false",
            sr1["original_F1_scientific_execution"] is False
            and dr1["original_F1_PASS_claimed"] is False
            and dr1["projection_executed"] is False
            and dr1["CV_mass_inversion_executed"] is False,
        )
        gate(
            "F1R1_F1R2_handoff_authorized",
            hr1["milestone"] == MILESTONE
            and hr1["authorized"] is True
            and hr1["execution"] is True,
            hr1,
        )
        gate(
            "F1R1_F2_and_downstream_still_unauthorized",
            hr1["F2_authorized"] is False
            and hr1["F2_execution_authorized"] is False
            and hr1["F3_authorized"] is False
            and hr1["A3_E2_authorized"] is False
            and hr1["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind formal E1-R2 result.
        # ------------------------------------------------------------------------------------------
        stage = "E1R2_binding"

        e1 = drive / E1R2_REL
        gate("E1R2_output_present", e1.is_dir(), str(e1))
        m1 = verify_manifest(e1, E1R2_MANIFEST)
        gate("E1R2_manifest_exact_9", len(m1) == 9, len(m1))

        s1 = load_json(e1 / E1R2_SUMMARY)
        c1 = load_json(e1 / E1R2_CLASSIFICATION)
        d1 = load_json(e1 / E1R2_DECISION)

        gate("E1R2_status_exact", s1["status"] == E1R2_STATUS, s1["status"])
        gate(
            "E1R2_representation_PASS_structural_restart_incompatibility",
            s1["representation_only_PASS"] is True
            and s1["classification"] == "STRUCTURAL_RESTART_INCOMPATIBILITY"
            and d1["representation_reconstruction_PASS"] is True
            and d1["structural_restart_incompatibility"] is True,
        )
        gate(
            "E1R2_required_parent_projection_and_restart_contract",
            "mass-conservative grid-to-streamline parent-state projection"
            in " ".join(c1["required_before_any_checkpoint_test"])
            and "restart temporal contract"
            in " ".join(c1["required_before_any_checkpoint_test"]),
            c1["required_before_any_checkpoint_test"],
        )
        gate(
            "E1R2_downstream_firewalls",
            c1["checkpoint_committed_reuse"] is False
            and c1["A3_E2_checkpoint_test_authorized"] is False
            and c1["teacher_backed_test_authorized_now"] is False
            and c1["AV4_dynamic_transport_execution_authorized"] is False
            and d1["A3_E2_checkpoint_test_authorized"] is False
            and d1["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind A2-E exact parent state and refreshed geometry authority.
        # ------------------------------------------------------------------------------------------
        stage = "A2E_parent_state_binding"

        a2 = drive / A2E_REL
        gate("A2E_output_present", a2.is_dir(), str(a2))
        m2 = verify_manifest(a2, A2E_MANIFEST)
        gate("A2E_manifest_exact_12", len(m2) == 12, len(m2))
        gate("A2E_epoch_manifested", A2E_EPOCH in m2, A2E_EPOCH)

        s2 = load_json(a2 / A2E_SUMMARY)
        gate("A2E_status_exact", s2["status"] == A2E_STATUS, s2["status"])
        gate(
            "A2E_parent_day_and_case_exact",
            s2["control_realization"] == CONTROL_REALIZATION
            and s2["paired_porosity"] == CONTROL_POROSITY
            and float(s2["canonical_day"]) == PARENT_DAY,
        )
        gate(
            "A2E_same_time_firewall",
            s2["PI_RNN_inference"] is False
            and s2["physical_time_advance"] is False
            and s2["AV3_checkpoint_committed_reuse"] is False,
        )

        with np.load(a2 / A2E_EPOCH, allow_pickle=False) as z:
            epoch_keys = set(z.files)
            parent_mass_shape = tuple(np.asarray(z["parent_component_mass_kg"]).shape)
            reconciled_shape = tuple(np.asarray(z["reconciled_saturation"]).shape)
            pressure_shape = tuple(np.asarray(z["refreshed_pressure_psi"]).shape)
            xyz_shape = tuple(np.asarray(z["streamline_xyz_m"]).shape)
            tof_shape = tuple(np.asarray(z["streamline_tof_s"]).shape)
            weight_shape = tuple(np.asarray(z["streamline_weight_m3_s"]).shape)
            canonical_day = float(np.asarray(z["canonical_day"]).reshape(-1)[0])

        required_epoch = {
            "parent_component_mass_kg",
            "reconciled_saturation",
            "refreshed_pressure_psi",
            "paired_porosity",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "canonical_day",
        }
        gate(
            "A2E_restart_authority_arrays_present",
            required_epoch.issubset(epoch_keys),
            sorted(required_epoch),
        )
        gate(
            "A2E_restart_authority_shapes_exact",
            parent_mass_shape == GRID
            and reconciled_shape == GRID
            and pressure_shape == GRID
            and xyz_shape == (NSL, NN, 3)
            and tof_shape == (NSL, NN)
            and weight_shape == (NSL,),
            {
                "parent_mass": parent_mass_shape,
                "reconciled_saturation": reconciled_shape,
                "pressure": pressure_shape,
                "xyz": xyz_shape,
                "tof": tof_shape,
                "weight": weight_shape,
            },
        )
        gate("A2E_epoch_day365_exact", canonical_day == PARENT_DAY, canonical_day)

        # ------------------------------------------------------------------------------------------
        # Bind frozen halo-domain semantics.
        # ------------------------------------------------------------------------------------------
        stage = "R7R7D_halo_semantics_binding"

        r7d = drive / R7R7D_REL
        gate("R7R7D_output_present", r7d.is_dir(), str(r7d))
        md = verify_manifest(r7d, R7R7D_MANIFEST)
        gate("R7R7D_manifest_nonempty", len(md) > 0, len(md))

        sd = load_json(r7d / R7R7D_SUMMARY)
        pd = load_json(r7d / R7R7D_PROTOCOL)

        gate("R7R7D_status_exact", sd["status"] == R7R7D_STATUS, sd["status"])
        gate("R7R7D_protocol_exact", sd["protocol_id"] == R7R7D_PROTOCOL_ID, sd["protocol_id"])
        gate(
            "R7R7D_single_nonrecursive_same_layer_xy_halo",
            pd["new_halo_set_H1"]["recursive_growth"] is False
            and pd["new_halo_set_H1"]["same_layer_only"] is True
            and pd["new_halo_set_H1"]["vertical_neighbors_allowed"] is False
            and pd["new_halo_set_H1"]["diagonal_neighbors_allowed"] is False,
        )
        gate(
            "R7R7D_halo_terminal_sink_semantics",
            pd["new_halo_set_H1"]["role"] == "terminal finite-volume occupancy sinks only"
            and pd["graph_semantics"]["H1_to_S0_reverse_edges"] is False
            and pd["graph_semantics"]["H1_to_H1_edges"] is False
            and pd["graph_semantics"]["H1_as_transit_nodes"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Source-level audit of SG7D/E37A reverse-transfer ingredients.
        # ------------------------------------------------------------------------------------------
        stage = "existing_reverse_transfer_source_audit"

        e37_text = (root / E37A).read_text(encoding="utf-8", errors="replace")
        sg7d_text = (root / SG7D).read_text(encoding="utf-8", errors="replace")

        gate(
            "SG7D_subsegment_operator_exact_ingredients_present",
            "def build_subsegment_operator" in sg7d_text
            and "pv = (" in sg7d_text
            and "q" in sg7d_text
            and "delta_tau" in sg7d_text
            and '"flat_cell"' in sg7d_text,
        )
        gate(
            "E37A_existing_grid_sampler_present",
            "def sample_grid_inventory_to_control_volumes" in e37_text
            and "sub_mass = pv * sub_rho * sub_sg" in e37_text
            and "cv_mass = np.bincount" in e37_text,
        )
        gate(
            "E37A_existing_sampler_not_exact_A2E_mass_authority",
            "parent_component_mass_kg" not in e37_text[
                e37_text.find("def sample_grid_inventory_to_control_volumes"):
                e37_text.find(
                    "\ndef ",
                    e37_text.find("def sample_grid_inventory_to_control_volumes") + 5
                )
            ],
            "existing helper samples saturation-derived subsegment inventory; "
            "F1 requires exact Cartesian parent_component_mass_kg authority",
        )
        gate(
            "E37A_existing_sampler_closure_is_internal_CV_inversion_only",
            "closure = float(np.sum(reconstructed) - np.sum(cv_mass))" in e37_text,
        )
        gate(
            "E37A_CV_mass_inversion_authority_present_for_F2",
            "def invert_cv_mass_to_saturation" in e37_text
            and "cv_pressure_mass_coeff" in e37_text,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze exact restart-state authority.
        # ------------------------------------------------------------------------------------------
        stage = "restart_state_authority_freeze"

        restart_state = {
            "milestone": MILESTONE,
            "parent_epoch": {
                "day": PARENT_DAY,
                "realization": CONTROL_REALIZATION,
                "paired_porosity": CONTROL_POROSITY,
                "source_artifact": A2E_EPOCH,
                "source_artifact_sha256": m2[A2E_EPOCH],
            },
            "authoritative_parent_component_mass": {
                "array": "parent_component_mass_kg",
                "shape": list(GRID),
                "role": (
                    "primary conserved recurrent state; never reconstructed from saturation "
                    "when exact A2-E cellwise component mass is available"
                ),
            },
            "same_time_parent_saturation": {
                "array": "reconciled_saturation",
                "shape": list(GRID),
                "role": (
                    "saturation consistent with the same exact parent component mass under "
                    "the refreshed Day365 pressure field"
                ),
                "parent_saturation_array_role": (
                    "historical pre-refresh saturation reference only; not the accepted "
                    "restart saturation after the A2-E pressure/saturation reconciliation"
                ),
            },
            "refreshed_flow_geometry": {
                "pressure": "refreshed_pressure_psi",
                "streamline_xyz": "streamline_xyz_m",
                "streamline_tof": "streamline_tof_s",
                "streamline_weight": "streamline_weight_m3_s",
                "streamlines": NSL,
                "nodes": NN,
                "transport_control_volumes": NCV,
            },
            "recurrent_state_principle": (
                "Cartesian component mass is the authoritative global recurrent physical state. "
                "Streamline control-volume mass is a conservative transport-coordinate representation "
                "derived from that state at each refreshed-flow epoch."
            ),
        }

        # ------------------------------------------------------------------------------------------
        # Freeze conservative normalized-transpose + residual projection.
        # ------------------------------------------------------------------------------------------
        stage = "parent_projection_protocol_freeze"

        projection = {
            "milestone": MILESTONE,
            "name": "Exact-support normalized-transpose mass projection with residual grid sidecar",
            "execution_in_F1": False,
            "geometry_authority": {
                "subsegment_operator": "frozen SG7D build_subsegment_operator",
                "operator_fields": [
                    "streamline",
                    "node",
                    "flat_cell",
                    "pv_m3",
                    "k",
                    "j",
                    "i",
                ],
                "refreshed_geometry_source": A2E_EPOCH,
                "control_volume_index": "r = streamline*200 + node",
            },
            "exact_support_S0": {
                "definition": (
                    "unique Cartesian flat_cell indices present in the refreshed SG7D "
                    "subsegment operator"
                ),
                "parent_mass_eligibility": (
                    "only exact mass in S0 is projected onto refreshed streamline CVs"
                ),
            },
            "normalized_transpose": {
                "cell_denominator": "W_c = sum_{q: c(q)=c} PV_q",
                "subsegment_mass_assignment": (
                    "m_q = M_parent[c(q)] * PV_q / W_c"
                ),
                "control_volume_mass": (
                    "M_cv[r] = sum_{q: r(q)=r} m_q"
                ),
                "properties_if_executed_exactly": [
                    "nonnegative parent cell mass produces nonnegative subsegment/CV mass",
                    "each S0 parent cell mass is partitioned exactly once across its overlapping subsegments",
                    "sum(M_cv) = sum(M_parent on S0) up to numerical roundoff",
                    "overlapping streamline occupancy cannot duplicate authoritative Cartesian mass",
                ],
            },
            "residual_grid_sidecar": {
                "definition": (
                    "R_grid[c] = 0 for c in S0; R_grid[c] = M_parent[c] for c not in S0"
                ),
                "global_ledger": (
                    "sum(M_cv) + sum(R_grid) = sum(M_parent_grid)"
                ),
                "H1_policy": (
                    "H1/off-streamline mass remains exact grid-residual mass; it is not "
                    "reverse-moved through forbidden H1->S0 arcs"
                ),
                "outside_D1_policy": (
                    "mass outside refreshed D1 is also retained exactly in the residual "
                    "grid sidecar and reported separately"
                ),
                "physical_transport_claim": False,
            },
            "CV_saturation_recovery_for_F2": {
                "authority": "E37A invert_cv_mass_to_saturation",
                "pressure_coefficient": "E37A cv_pressure_mass_coeff built from refreshed pressure",
                "capacity_check_required": True,
                "execution_in_F1": False,
            },
            "existing_E37A_sampler_role": {
                "function": "sample_grid_inventory_to_control_volumes",
                "role": (
                    "diagnostic comparator only; it samples saturation-derived subsegment "
                    "inventory and does not establish equality to exact A2-E Cartesian "
                    "parent_component_mass_kg"
                ),
                "production_parent_projection_authority": False,
            },
            "prohibitions": [
                "no reverse H1->S0 physical transport",
                "no H1->H1 transit",
                "no recursive halo growth",
                "no global mass rescaling",
                "no component-mass clipping or discarding",
                "no replacement of exact parent_component_mass_kg by saturation-derived mass",
                "no checkpoint/model execution",
                "no physical-time advance",
            ],
        }

        residual_contract = {
            "milestone": MILESTONE,
            "state_blocks": [
                {
                    "name": "transport_CV_component_mass",
                    "shape": [NSL, NCV],
                    "authority": "normalized-transpose projection of exact S0 Cartesian mass",
                },
                {
                    "name": "transport_CV_saturation",
                    "shape": [NSL, NCV],
                    "authority": (
                        "E37A mass inversion after F2 capacity certification; derived state, "
                        "not primary conserved authority"
                    ),
                },
                {
                    "name": "grid_residual_component_mass",
                    "shape": list(GRID),
                    "authority": "exact A2-E parent mass outside refreshed S0",
                },
            ],
            "required_F2_diagnostics": [
                "S0 parent mass kg and fraction of total parent mass",
                "H1 residual mass kg and fraction",
                "outside-D1 residual mass kg and fraction",
                "total residual mass kg and fraction",
                "number of active-mass cells in S0, H1, and outside D1",
                "CV capacity excess if any",
                "exact global split-state mass ledger residual",
            ],
            "no_post_hoc_residual_fraction_threshold": True,
            "F2_outcome_classes": {
                "F2_PASS_CV_COMPLETE": (
                    "projection/conservation/capacity gates pass and residual mass is numerical zero"
                ),
                "F2_PASS_SPLIT_STATE_REQUIRED": (
                    "projection/conservation/capacity gates pass but physically nonzero residual "
                    "grid mass remains outside refreshed S0"
                ),
                "F2_SCIENTIFIC_FAIL_CV_CAPACITY": (
                    "normalized-transpose assigned CV mass cannot be inverted within frozen "
                    "physical saturation/capacity bounds"
                ),
                "F2_TECHNICAL_BLOCK": (
                    "authority/schema/source failure before a valid scientific decision"
                ),
            },
        }

        temporal = {
            "milestone": MILESTONE,
            "restart_semantics": {
                "parent_time_days": PARENT_DAY,
                "first_candidate_target_time_days": FIRST_CANDIDATE_TARGET_DAY,
                "first_candidate_delta_time_days": FIRST_CANDIDATE_DELTA_DAY,
                "parent_time_hat_reference": PARENT_DAY / 1000.0,
                "target_time_hat_reference": FIRST_CANDIDATE_TARGET_DAY / 1000.0,
                "delta_time_hat_reference": FIRST_CANDIDATE_DELTA_DAY / 1000.0,
                "delta_eta_definition": (
                    "delta_eta_streamline = delta_time_days*86400/tau_end_s "
                    "using the refreshed parent-epoch Pollock terminal TOF"
                ),
            },
            "required_future_model_information": [
                "parent-state component mass and/or a lossless state-conditioned representation",
                "refreshed flow/geometry conditioning",
                "explicit elapsed restart interval delta_t",
            ],
            "legacy_AV3_absolute_time_features": {
                "retained_as_diagnostic_reference": True,
                "sufficient_restart_semantics": False,
                "delta_time_substitution_into_old_target_time_hat": False,
            },
            "neural_input_dimension_frozen_in_F1": False,
            "reason": (
                "F2 must quantify the residual grid-state burden before the final restartable "
                "model signature and dimensionality are frozen."
            ),
            "teacher_execution_authorized": False,
            "checkpoint_inference_authorized": False,
            "physical_time_advance_authorized": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze F2 execution handoff.
        # ------------------------------------------------------------------------------------------
        stage = "F2_handoff_freeze"

        handoff = {
            "milestone": "POSTV16-AV4-F2",
            "name": "Controlled Day365 Conservative Parent-State Projection Execution",
            "authorized": True,
            "execution": True,
            "control_realization": CONTROL_REALIZATION,
            "paired_porosity": CONTROL_POROSITY,
            "parent_day": PARENT_DAY,
            "allowed": [
                "rebuild refreshed SG7D subsegment operator from the exact A2-E epoch",
                "construct refreshed S0 and frozen one-ring same-layer x/y H1 for diagnostics",
                "execute the normalized-transpose exact-mass projection from S0 cells to 1078x200 CVs",
                "construct exact residual grid mass sidecar outside S0",
                "build refreshed E37A CV pressure-mass coefficients",
                "test CV mass capacity and invert projected CV mass to parent CV saturation",
                "certify global split-state mass closure",
                "classify CV_COMPLETE vs SPLIT_STATE_REQUIRED vs CV_CAPACITY_FAIL",
            ],
            "forbidden": [
                "teacher transport",
                "checkpoint model load or inference",
                "physical-time advance",
                "future-state prediction",
                "streamline-to-grid future mapback",
                "training or checkpoint reselection",
                "normalization refit",
                "locked-OOD tuning",
                "CMG",
                "automatic support-domain expansion after observing F2 outcome",
            ],
            "F3_teacher_or_restart_model_protocol_authorized": False,
            "A3_E2_checkpoint_test_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "E1R2_structural_restart_incompatibility_bound": True,
            "A2E_parent_mass_authority_bound": True,
            "SG7D_refreshed_geometry_authority_bound": True,
            "E37A_CV_mass_inversion_authority_bound": True,
            "R7R7D_halo_semantics_bound": True,
            "split_restart_state_contract_frozen": True,
            "normalized_transpose_projection_frozen": True,
            "residual_grid_sidecar_frozen": True,
            "explicit_restart_temporal_semantics_frozen": True,
            "neural_input_dimension_frozen": False,
            "projection_executed": False,
            "CV_mass_inversion_executed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "training_performed": False,
            "mapback_performed": False,
            "CMG_validation_performed": False,
            "F2_authorized": True,
            "F2_execution_authorized": True,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "parent_day": PARENT_DAY,
            "first_candidate_target_day": FIRST_CANDIDATE_TARGET_DAY,
            "first_candidate_delta_day": FIRST_CANDIDATE_DELTA_DAY,
            "parent_state_authority": "A2-E exact parent_component_mass_kg",
            "accepted_same_time_saturation": "A2-E reconciled_saturation",
            "transport_state_shape": [NSL, NCV],
            "global_state_shape": list(GRID),
            "projection": "S0 normalized transpose + exact residual grid sidecar",
            "reverse_halo_pullback": False,
            "existing_E37A_sampler_production_authority": False,
            "neural_input_dimension_frozen": False,
            "projection_execution": False,
            "teacher_transport": False,
            "checkpoint_inference": False,
            "physical_time_advance": False,
            "F2_authorized": True,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_F1_R2_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F1_R2_Restart_State_Authority_Contract.json":
                json_bytes(restart_state),
            "POSTV16_AV4_F1_R2_Conservative_Grid_to_Streamline_Projection_Protocol.json":
                json_bytes(projection),
            "POSTV16_AV4_F1_R2_Residual_Grid_State_Sidecar_Contract.json":
                json_bytes(residual_contract),
            "POSTV16_AV4_F1_R2_Restart_Temporal_Semantics_Contract.json":
                json_bytes(temporal),
            "POSTV16_AV4_F1_R2_F2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F1_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F1_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": name, **value} for name, value in gates.items()]),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F1_R2_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })

        immutable_publish(
            out,
            {
                "POSTV16_AV4_F1_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: RESTART-STATE / CONSERVATIVE PARENT-PROJECTION PROTOCOL FREEZE PASS")
        print("=" * 214)
        print("E1-R2 structural incompatibility         : BOUND")
        print("A2-E exact parent component mass          : BOUND")
        print("Accepted restart saturation               : A2-E reconciled_saturation")
        print("Refreshed SG7D / E37A geometry            : BOUND")
        print("Parent transport state                    : 1078 x 200 CV component mass")
        print("Residual parent state                     : exact Cartesian mass outside refreshed S0")
        print("Reverse halo pullback                     : FORBIDDEN")
        print("Projection execution                      : False")
        print("CV mass inversion execution               : False")
        print("Teacher / checkpoint inference            : False / False")
        print("Physical time advance                     : False")
        print("POSTV16-AV4-F2                            : AUTHORIZED")
        print("F2 execution                              : AUTHORIZED")
        print("F3 / A3-E2 / AV4 dynamic transport       : NOT AUTHORIZED")
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
            "projection_executed": False,
            "CV_mass_inversion_executed": False,
            "teacher_transport_performed": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "training_performed": False,
            "mapback_performed": False,
            "F2_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F1_R2_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV4_F1_R2_Blocked_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
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
