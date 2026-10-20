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


MILESTONE = "POSTV16-AV3-A3-R1"
PROTOCOL_ID = (
    "POSTV16_AV3_A3_R1_FIRST9_CELL_CENTERED_GEOMETRY_AND_"
    "TRAIN_NORMALIZATION_AUTHORITY_CORRECTION_V1"
)

STATUS_PASS = (
    "AV3A3R1_FIRST_NINE_CHANNEL_CELL_CENTERED_GEOMETRY_AND_"
    "TRAIN_NORMALIZATION_AUTHORITY_CORRECTION_FROZEN_NO_A4_EXECUTION"
)

STATUS_BLOCKED = "AV3A3R1_AUTHORITY_CORRECTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A3_COMMIT = "d52d820a2ece185bc8e2799bf879e977a3ff856d"

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

A2 = "PAD_Stream_POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV2A3 = "PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py"
AV2A3_BLOB = "9b209abc3a2abb905b9250a16344e52160e61c47"

B3 = "PAD_Stream_V16B3_Independent_FMM_Pollock_TOF_Comparison.py"
B3_BLOB = "1f04056d039d698707991646f086f5dc320a04ca"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

SOURCE_BLOBS = {
    A3: A3_BLOB,
    A2: A2_BLOB,
    AV2A3: AV2A3_BLOB,
    B3: B3_BLOB,
    C2: C2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal A3 output authority.
# --------------------------------------------------------------------------------------------------

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

A3_REL = BASE_AV3 / "POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze"
A3_SUMMARY = "PAD_Stream_POSTV16_AV3_A3_Summary.json"
A3_MODEL = "POSTV16_AV3_A3_13Channel_PIRNN_Training_Protocol.json"
A3_HANDOFF = "POSTV16_AV3_A3_A4_Handoff_Contract.json"
A3_DECISION = "POSTV16_AV3_A3_Decision_Contract.json"
A3_MANIFEST = "POSTV16_AV3_A3_Artifact_Manifest.csv"

A3_STATUS = (
    "AV3A3_SPATIAL_COREY_RELPERM_TRANSPORT_TEACHER_RESIDUAL_AND_"
    "13CHANNEL_PIRNN_PROTOCOL_PROSPECTIVELY_FROZEN_NO_TEACHER_OR_TRAINING_EXECUTION"
)

OUT_REL = BASE_AV3 / "POSTV16_AV3_A3_R1_First9_CellCentered_Geometry_and_Normalization_Authority_Correction"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A3_R1_BLOCKED"

DX_M = 6.096
DY_M = 6.096
DZ_M = 1.2192

ORIGIN_CENTER_M = np.asarray(
    [DX_M / 2.0, DY_M / 2.0, DZ_M / 2.0],
    dtype=np.float64,
)

FIRST9 = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]

NEW4 = [
    "nw_hat",
    "no_hat",
    "krw_max_hat",
    "kro_max_hat",
]

CORRECTED_SPATIAL_FIRST9 = [
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
]

UNCHANGED_FIRST9 = [
    "xi",
    "pollock_tau_hat",
    "target_time_hat",
    "target_eta_sequence",
]


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
            raise GateError("manifest_SHA:" + fn)

    return manifest


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
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
    w = csv.DictWriter(
        s,
        fieldnames=fields,
        lineterminator="\n",
    )
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
    assert np.array_equal(
        ORIGIN_CENTER_M,
        np.asarray(
            [3.048, 3.048, 0.6096],
            dtype=np.float64,
        ),
    )

    assert len(FIRST9) == 9
    assert len(NEW4) == 4
    assert len(FIRST9 + NEW4) == 13

    assert set(CORRECTED_SPATIAL_FIRST9).issubset(set(FIRST9))
    assert set(UNCHANGED_FIRST9).issubset(set(FIRST9))
    assert set(CORRECTED_SPATIAL_FIRST9).isdisjoint(set(UNCHANGED_FIRST9))
    assert set(CORRECTED_SPATIAL_FIRST9 + UNCHANGED_FIRST9) == set(FIRST9)

    print("POSTV16-AV3-A3-R1 first-nine-channel authority-correction self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)

        gates[name] = {
            "passed": ok,
            "value": value,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )

        if not ok:
            raise GateError(name)

    print("=" * 204)
    print("POSTV16-AV3-A3-R1 — FIRST-NINE-CHANNEL CELL-CENTERED GEOMETRY / NORMALIZATION AUTHORITY CORRECTION")
    print("=" * 204)
    print("DESIGN / AUTHORITY-CORRECTION FREEZE ONLY.")
    print("THE FORMAL A3 PASS REMAINS IMMUTABLE AND IS NOT RECLASSIFIED.")
    print("THE HISTORICAL AV2-A3 RESULT REMAINS IMMUTABLE AND IS NOT RECLASSIFIED.")
    print("NO A4 TEACHER GENERATION. NO Y GENERATION. NO TRAINING. NO INFERENCE.")
    print("NO CHECKPOINT CREATION. NO OOD TARGET ACCESS. NO PRESSURE RE-SOLVE. NO POLLOCK RETRACE.")
    print("NO MAPBACK. NO LP. NO CMG.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_formal_AV3A3_commit",
            parent == PARENT_A3_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = (
                git_blob(p, root)
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind formal A3 PASS.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A3_binding"

        a3 = drive / A3_REL

        gate(
            "AV3A3_output_present",
            a3.is_dir(),
            str(a3),
        )

        m3 = verify_manifest(
            a3,
            A3_MANIFEST,
        )

        gate(
            "AV3A3_manifest_SHA_closure",
            len(m3) == 10,
            len(m3),
        )

        s3 = load_json(
            a3 / A3_SUMMARY
        )

        model3 = load_json(
            a3 / A3_MODEL
        )

        h3 = load_json(
            a3 / A3_HANDOFF
        )

        d3 = load_json(
            a3 / A3_DECISION
        )

        gate(
            "AV3A3_status_exact",
            s3["status"] == A3_STATUS,
            s3["status"],
        )

        gate(
            "AV3A3_formal_PASS_preserved",
            d3["AV3_A4_authorized"] is True,
        )

        gate(
            "AV3A3_no_teacher_generation",
            d3["teacher_generation_performed"] is False,
        )

        gate(
            "AV3A3_no_training",
            d3["training_performed"] is False,
        )

        gate(
            "AV3A3_no_locked_OOD_target_access",
            d3["locked_OOD_target_accessed"] is False,
        )

        gate(
            "AV3A3_A4_handoff_was_prospective",
            h3["milestone"] == "POSTV16-AV3-A4",
            h3["milestone"],
        )

        gate(
            "AV3A3_first9_reuse_statement_present",
            "reuse frozen AV2 train-authority representations/scales"
            in model3["normalization"]["first_9_channels"],
            model3["normalization"]["first_9_channels"],
        )

        # ------------------------------------------------------------------------------------------
        # Source-level authority mismatch evidence.
        # ------------------------------------------------------------------------------------------
        stage = "authority_mismatch_audit"

        av2a3_src = (root / AV2A3).read_text(
            encoding="utf-8",
            errors="replace",
        )

        b3_src = (root / B3).read_text(
            encoding="utf-8",
            errors="replace",
        )

        c2_src = (root / C2).read_text(
            encoding="utf-8",
            errors="replace",
        )

        a2_src = (root / A2).read_text(
            encoding="utf-8",
            errors="replace",
        )

        # Historical AV2-A3 explicitly creates and passes a zero origin to
        # C2 trilinear sampling when rebuilding spatial predictor channels.
        zero_origin_markers = [
            "origin = np.array(",
            "[0.0, 0.0, 0.0]",
            "c2.trilinear(",
        ]

        for marker in zero_origin_markers:
            gate(
                "historical_AV2A3_marker_" + hashlib.sha256(marker.encode()).hexdigest()[:10],
                marker in av2a3_src,
                marker,
            )

        # V16B3 freezes cell-centered origin inference, with half-cell origin
        # preferred when both origin conventions satisfy box bounds.
        b3_markers = [
            "CELL_CENTER_COORDINATES",
            "origin_center",
            "np.array([dx/2, dy/2, dz/2])",
            "prefer physical cell-center convention",
        ]

        for marker in b3_markers:
            gate(
                "V16B3_cell_center_marker_" + hashlib.sha256(marker.encode()).hexdigest()[:10],
                marker in b3_src,
                marker,
            )

        c2_markers = [
            "SAME trilinear cell-centered interpolation geometry",
            "already frozen",
            "origin_center_m",
        ]

        for marker in c2_markers:
            gate(
                "V16C2_mapping_marker_" + hashlib.sha256(marker.encode()).hexdigest()[:10],
                marker in c2_src,
                marker,
            )

        a2_markers = [
            "ORIGIN_CENTER_M",
            "[DX_M / 2.0, DY_M / 2.0, DZ_M / 2.0]",
            "V16B3_V16C2_cell_centered_sampling_origin_exact",
        ]

        for marker in a2_markers:
            gate(
                "AV3A2_corrected_origin_marker_" + hashlib.sha256(marker.encode()).hexdigest()[:10],
                marker in a2_src,
                marker,
            )

        gate(
            "correct_cell_center_origin_numeric",
            np.array_equal(
                ORIGIN_CENTER_M,
                np.asarray(
                    [3.048, 3.048, 0.6096],
                    dtype=np.float64,
                ),
            ),
            ORIGIN_CENTER_M.tolist(),
        )

        # ------------------------------------------------------------------------------------------
        # Freeze corrected A4 first-nine-channel authority.
        # ------------------------------------------------------------------------------------------
        stage = "corrected_A4_authority_freeze"

        correction = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "scope": (
                "Correct only the AV3-A4 predictor/physics-sidecar spatial sampling "
                "and dependent TRAIN-only pressure normalization authority. "
                "Do not alter the A3 PDE, face discretization, model architecture, "
                "loss weights, split registry, constitutive fields, pressure/Q solution, "
                "Pollock paths/TOF, R7D graph geometry, or historical AV2 results."
            ),
            "formal_AV3A3_result": {
                "status_preserved": A3_STATUS,
                "reclassified": False,
                "reason": (
                    "A3 correctly froze its tested design contracts and performed no "
                    "teacher/training execution. This R1 closes a subsequently detected "
                    "cross-authority geometry mismatch before A4 execution."
                ),
            },
            "historical_AV2A3_result": {
                "reclassified": False,
                "role": "immutable historical AV2 authority/result only",
                "AV3_direct_X9_reuse_authorized": False,
            },
            "detected_mismatch": {
                "historical_AV2A3_spatial_sampling_origin": [0.0, 0.0, 0.0],
                "current_V16B3_V16C2_AV3A2_cell_center_origin_m":
                    ORIGIN_CENTER_M.tolist(),
                "affected_AV3_first9_channels": CORRECTED_SPATIAL_FIRST9,
                "unaffected_AV3_first9_channels": UNCHANGED_FIRST9,
                "new_AV3_constitutive_channels_already_corrected_in_A2": NEW4,
            },
        }

        first9 = {
            "channel_order": FIRST9,
            "cell_center_origin_m": ORIGIN_CENTER_M.tolist(),
            "grid_spacing_m": [DX_M, DY_M, DZ_M],
            "channel_authority": {
                "xi": (
                    "unchanged deterministic 201-node streamline coordinate; "
                    "same AV2 realization-specific node order"
                ),
                "pollock_tau_hat": (
                    "unchanged Pollock_TOF/terminal_Pollock_TOF from exact paired AV2 kinematics"
                ),
                "adv_tau_hat": (
                    "reconstruct deterministic ADV travel-time grid from frozen paired AV2 "
                    "pore-velocity fields using the exact historical ADV solver, then sample "
                    "with V16B3/V16C2 cell-centered origin [dx/2,dy/2,dz/2], and divide by "
                    "terminal Pollock TOF"
                ),
                "log10_Kh": (
                    "sample frozen Foundation Kx/Ky onto paired Pollock XYZ with the "
                    "cell-centered origin, then log10(sqrt(Kx*Ky))"
                ),
                "log10_Kz_over_Kh": (
                    "sample frozen Foundation Kz plus Kx/Ky with the cell-centered origin, "
                    "then log10(Kz/Kh)"
                ),
                "porosity": (
                    "sample the paired frozen AV2 porosity grid onto paired Pollock XYZ "
                    "with the cell-centered origin"
                ),
                "pressure_z": (
                    "sample the frozen Foundation pressure grid onto paired Pollock XYZ "
                    "with the cell-centered origin, then apply the newly fitted corrected "
                    "TRAIN-only pressure z-score"
                ),
                "target_time_hat": "unchanged target_days/1000",
                "target_eta_sequence": (
                    "unchanged target_days*86400/terminal_Pollock_TOF, repeated on 201 nodes"
                ),
            },
            "direct_reuse_of_historical_AV2A3_X_required_9": False,
            "historical_AV2A3_X9_role": (
                "historical comparison/audit only; not the AV3-A4 production predictor tensor"
            ),
        }

        normalization = {
            "pressure_z": {
                "fit_required": True,
                "fit_domain": (
                    "corrected cell-centered pressure samples from AV3CR0001 and AV3CR0002 "
                    "paired Pollock nodes only"
                ),
                "statistic": "z=(pressure_psi-TRAIN_mean)/TRAIN_std",
                "validation_used_for_fit": False,
                "locked_OOD_used_for_fit": False,
                "historical_AV2A3_pressure_mean_std_direct_reuse": False,
                "reason": (
                    "The sampled pressure representation changes when the interpolation "
                    "origin changes, so its fitted mean/std must be recomputed prospectively "
                    "from corrected TRAIN predictor nodes."
                ),
            },
            "new_constitutive_channels": {
                "nw_hat": "(nw-3.0)/1.0",
                "no_hat": "(no-3.0)/1.0",
                "krw_max_hat": "(krw_max-0.80)/0.20",
                "kro_max_hat": "(kro_max-0.80)/0.20",
                "fit_required": False,
            },
            "other_first9_channels": {
                "fit_required": False,
            },
            "streamline_weight": {
                "model_input": False,
                "geometry_correction_required": False,
            },
        }

        physics_sidecar = {
            "phi_sequence": (
                "must be exactly the corrected cell-centered porosity channel used in X13 "
                "for the corresponding realization/streamline"
            ),
            "metric_M": "reconstruct from frozen paired Pollock XYZ/TOF; unchanged by grid sampling origin",
            "metric_M_face": "reconstruct from frozen paired Pollock XYZ/TOF; unchanged",
            "control_volume_dtheta": "reconstruct from frozen paired Pollock XYZ/TOF; unchanged",
            "dtheta_center": "reconstruct from frozen paired Pollock TOF; unchanged",
            "terminal_pollock_tof_s": "reuse paired frozen AV2 TOF terminal values",
            "nw_sequence": "reuse exact corrected A2 nw_streamline",
            "no_sequence": "reuse exact corrected A2 no_streamline",
            "krw_max_sequence": "reuse exact corrected A2 krw_max_streamline",
            "kro_max_sequence": "reuse exact corrected A2 kro_max_streamline",
            "consistency_gate": (
                "X13 porosity channel and physics-sidecar phi_sequence must be array-identical "
                "for every realization and node."
            ),
        }

        preserved = {
            "A3_spatial_constitutive_PDE": True,
            "A3_teacher_face_discretization": True,
            "A3_teacher_residual_face_algebra_match": True,
            "A3_13channel_order": FIRST9 + NEW4,
            "A3_model_parameters": 53057,
            "A3_objective": "L_data + 0.01 L_phys",
            "A3_training_hyperparameters": True,
            "A3_train_validation_OOD_split": True,
            "A1_constitutive_field_model_and_seeds": True,
            "A2_constitutive_realizations": True,
            "pressure_Q_solution": "unchanged / no re-solve",
            "Pollock_paths_TOF": "unchanged / no retrace",
            "R7D_graph_geometry": "unchanged",
            "Swc_Sor": [0.20, 0.20],
        }

        handoff = {
            "milestone": "POSTV16-AV3-A4",
            "name": (
                "Corrected Cell-Centered TRAIN/VALIDATION Spatial-Corey/Relperm "
                "Teacher Generation, 13-Channel Dataset Assembly, "
                "Physics-Sidecar/Pair Registry, and Locked-OOD Predictor-Only Freeze"
            ),
            "authorized": True,
            "execution": True,
            "required_corrections": [
                "do not directly reuse historical AV2-A3 X_required_9 as AV3 production X9",
                "use cell-centered origin [dx/2,dy/2,dz/2] for every grid-to-streamline spatial channel",
                "reconstruct adv_tau_hat under the corrected cell-centered sampling geometry",
                "sample Kx/Ky/Kz, paired porosity, and pressure under the corrected geometry",
                "refit pressure_z mean/std using corrected AV3CR0001+AV3CR0002 TRAIN nodes only",
                "make predictor porosity channel array-identical to physics-sidecar phi_sequence",
                "append the exact four corrected A2 constitutive channels to form X13",
            ],
            "unchanged_A3_requirements": [
                "generate Y only for AV3CR0001, AV3CR0002, and AV3CR0003",
                "AV3CR0004 remains predictor-only until checkpoint freeze",
                "use the frozen A3 spatial-relperm teacher face algebra",
                "assemble TRAIN/VALIDATION adjacent-time physics pair registries",
                "no training or checkpoint creation in A4",
                "no pressure re-solve, Pollock retrace, mapback, LP, or CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "formal_AV3A3_PASS_preserved": True,
            "historical_AV2A3_result_preserved": True,
            "AV2A3_X9_direct_reuse_for_AV3_prohibited": True,
            "cell_centered_first9_reconstruction_required": True,
            "corrected_pressure_TRAIN_only_normalization_refit_required": True,
            "predictor_phi_equals_physics_sidecar_phi_required": True,
            "A3_PDE_changed": False,
            "A3_face_discretization_changed": False,
            "A3_model_architecture_changed": False,
            "A3_loss_weights_changed": False,
            "A1_A2_constitutive_fields_changed": False,
            "teacher_generation_performed": False,
            "Y_target_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "checkpoint_created": False,
            "locked_OOD_target_accessed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A4_authorized": True,
            "next": handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "formal_AV3A3_status_preserved": A3_STATUS,
            "detected_historical_AV2A3_spatial_origin_m": [0.0, 0.0, 0.0],
            "correct_AV3_cell_center_origin_m": ORIGIN_CENTER_M.tolist(),
            "corrected_spatial_first9_channels": CORRECTED_SPATIAL_FIRST9,
            "unchanged_first9_channels": UNCHANGED_FIRST9,
            "new_constitutive_channels_unchanged": NEW4,
            "historical_AV2A3_X9_direct_reuse": False,
            "pressure_normalization_refit_on_corrected_TRAIN_nodes": True,
            "teacher_generation": False,
            "training": False,
            "locked_OOD_target_access": False,
            "AV3_A4_authorized": True,
            "next": handoff,
        }

        evidence_rows = [
            {
                "authority": "historical_AV2A3",
                "role": "historical source behavior",
                "sampling_origin_m": "[0.0,0.0,0.0]",
                "AV3_action": "do not directly reuse X_required_9",
            },
            {
                "authority": "V16B3/V16C2",
                "role": "cell-centered grid-to-streamline interpolation geometry",
                "sampling_origin_m": str(ORIGIN_CENTER_M.tolist()),
                "AV3_action": "use for corrected spatial first-nine channels",
            },
            {
                "authority": "AV3A2",
                "role": "already-corrected constitutive field sampling",
                "sampling_origin_m": str(ORIGIN_CENTER_M.tolist()),
                "AV3_action": "reuse nw/no/krw_max/kro_max streamline arrays unchanged",
            },
        ]

        files = {
            "PAD_Stream_POSTV16_AV3_A3_R1_Summary.json":
                json_bytes(summary),

            "POSTV16_AV3_A3_R1_Authority_Mismatch_and_Evidence.json":
                json_bytes(correction),

            "POSTV16_AV3_A3_R1_First9_CellCentered_Channel_Contract.json":
                json_bytes(first9),

            "POSTV16_AV3_A3_R1_Corrected_Normalization_Contract.json":
                json_bytes(normalization),

            "POSTV16_AV3_A3_R1_Corrected_Physics_Sidecar_Contract.json":
                json_bytes(physics_sidecar),

            "POSTV16_AV3_A3_R1_Preserved_A3_Authorities.json":
                json_bytes(preserved),

            "POSTV16_AV3_A3_R1_A4_Handoff_Contract.json":
                json_bytes(handoff),

            "POSTV16_AV3_A3_R1_Decision_Contract.json":
                json_bytes(decision),

            "POSTV16_AV3_A3_R1_Authority_Evidence.csv":
                csv_bytes(evidence_rows),

            "POSTV16_AV3_A3_R1_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate": k,
                            **v,
                        }
                        for k, v in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            files,
        )

        manifest_rows = []

        for q in sorted(out.iterdir()):
            if (
                q.is_file()
                and q.name
                != "POSTV16_AV3_A3_R1_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": q.name,
                        "sha256": sha256_file(q),
                        "bytes": q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV3_A3_R1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 204)
        print("POSTV16-AV3-A3-R1: FIRST-NINE-CHANNEL AUTHORITY CORRECTION FREEZE PASS")
        print("=" * 204)
        print("Formal AV3-A3 PASS                         : PRESERVED")
        print("Historical AV2-A3 result                  : PRESERVED")
        print("Historical AV2-A3 X9 direct reuse         : PROHIBITED FOR AV3")
        print("Historical spatial sampling origin m       : [0.0, 0.0, 0.0]")
        print("Correct AV3 cell-center origin m           :", ORIGIN_CENTER_M.tolist())
        print("Spatial first-nine channels to reconstruct :", ", ".join(CORRECTED_SPATIAL_FIRST9))
        print("Unchanged first-nine channels              :", ", ".join(UNCHANGED_FIRST9))
        print("New constitutive channels                  : A2 CORRECTED / UNCHANGED")
        print("Pressure normalization                     : REFIT ON CORRECTED TRAIN NODES ONLY")
        print("Predictor porosity == physics phi sidecar  : REQUIRED")
        print("A3 PDE / face algebra / model / objective  : UNCHANGED")
        print("Teacher generation / training              : False / False")
        print("Locked OOD Y access                        : False")
        print("POSTV16-AV3-A4                             : AUTHORIZED")
        print("A4 execution                               : AUTHORIZED")
        print("=" * 204)

        return 0

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "formal_AV3A3_result_reclassified": False,
            "teacher_generation_performed": False,
            "Y_target_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "checkpoint_created": False,
            "locked_OOD_target_accessed": False,
            "AV3_A4_authorized": False,
        }

        q = blocked / "POSTV16_AV3_A3_R1_Blocked_Report.json"

        if not q.exists():
            q.write_bytes(
                json_bytes(report)
            )

        print()
        print("POSTV16-AV3-A3-R1: BLOCKED", stage, repr(exc))

        return 2


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )

    p.add_argument(
        "--self-test",
        action="store_true",
    )

    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
