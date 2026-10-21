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


MILESTONE = "POSTV16-AV4-A0"

PROTOCOL_ID = (
    "POSTV16_AV4_A0_DYNAMIC_PRESSURE_REFRESH_SATURATION_DEPENDENT_"
    "SPATIAL_MOBILITY_FEEDBACK_AUTHORITY_GAP_AND_PHYSICS_IMPACT_V1"
)

STATUS_PASS = (
    "AV4A0_DYNAMIC_PRESSURE_REFRESH_SATURATION_DEPENDENT_SPATIAL_MOBILITY_"
    "FEEDBACK_AUTHORITY_GAP_AND_PHYSICS_IMPACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

STATUS_BLOCKED = "AV4A0_AUTHORITY_GAP_PHYSICS_IMPACT_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_AV3F_COMMIT = "f86aaf77d75628d8204c1361ba68eeed7cf62ee1"

AV3F_STATUS = (
    "AV3_FINAL_SPATIAL_COREY_RELPERM_SCIENTIFIC_OUTCOME_FROZEN_"
    "AV4_DYNAMIC_FLOW_COUPLING_A0_AUTHORIZED"
)

CHECKPOINT_SHA = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)

BEST_EPOCH = 92
AV3_REALIZATIONS = 4
AV3_CANONICAL_TIMES = 9
AV3_INTEGRATED_STATES = 36

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

AV3F = (
    "PAD_Stream_POSTV16_AV3_F_"
    "Final_Spatial_Corey_Relperm_Outcome_Freeze_and_AV4_Handoff.py"
)
AV3F_BLOB = "4a24a0646048be58b9abebf113d87a165692c916"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

R3R3 = (
    "PAD_Stream_V16E41R3R3_"
    "Saturation_Updated_Flow_Refresh_Runtime_Architecture_Freeze.py"
)
R3R3_BLOB = "8d72895d023fe6c2d7d3c9752698a557747117a8"

R3R3R1 = (
    "PAD_Stream_V16E41R3R3R1_"
    "Mass_Conservative_Pressure_Refresh_Reconciliation_Architecture_Amendment.py"
)
R3R3R1_BLOB = "8087c864e85351859c771f744b81e82f995d6581"

AV3A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
AV3A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV3A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
AV3A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

AV3A6E = (
    "PAD_Stream_POSTV16_AV3_A6_E_"
    "Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
)
AV3A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"

SOURCE_BLOBS = {
    AV3F: AV3F_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    R3R2R1: R3R2R1_BLOB,
    R3R3: R3R3_BLOB,
    R3R3R1: R3R3R1_BLOB,
    AV3A2: AV3A2_BLOB,
    AV3A3: AV3A3_BLOB,
    AV3A6E: AV3A6E_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Frozen AV3-F Drive authority.
# --------------------------------------------------------------------------------------------------

BASE_AV3 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
)

AV3F_REL = BASE_AV3 / "POSTV16_AV3_F_Final_Outcome_Freeze_and_AV4_Handoff"

AV3F_SUMMARY = "PAD_Stream_POSTV16_AV3_F_Summary.json"
AV3F_CLAIMS = "POSTV16_AV3_F_Frozen_Scientific_Claims.json"
AV3F_HANDOFF = "POSTV16_AV3_F_AV4_Handoff_Contract.json"
AV3F_DECISION = "POSTV16_AV3_F_Decision_Contract.json"
AV3F_MANIFEST = "POSTV16_AV3_F_Artifact_Manifest.csv"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
    / "POSTV16_AV4_A0_Dynamic_Flow_Authority_Gap_and_Physics_Impact_Freeze"
)

BLOCK_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
    / "POSTV16_AV4_A0_BLOCKED"
)

# --------------------------------------------------------------------------------------------------
# Frozen AV3 constitutive parameter semantics.
# --------------------------------------------------------------------------------------------------

SWC = 0.20
SOR = 0.20
SPAN = 1.0 - SWC - SOR

MU_W_CP = 0.50
MU_O_CP = 5.00

NW_RANGE = (2.0, 4.0)
NO_RANGE = (2.0, 4.0)
KRW_MAX_RANGE = (0.60, 1.00)
KRO_MAX_RANGE = (0.60, 1.00)

GRID = (15, 50, 50)


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


def av3_spatial_mobility(
    saturation: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:

    S = np.asarray(
        saturation,
        dtype=np.float64,
    )

    Se = np.clip(
        (
            S
            - SWC
        )
        / SPAN,
        0.0,
        1.0,
    )

    krw = (
        np.asarray(
            krw_max,
            dtype=np.float64,
        )
        * Se
        ** np.asarray(
            nw,
            dtype=np.float64,
        )
    )

    kro = (
        np.asarray(
            kro_max,
            dtype=np.float64,
        )
        * (
            1.0
            - Se
        )
        ** np.asarray(
            no,
            dtype=np.float64,
        )
    )

    return (
        krw
        / MU_W_CP
        +
        kro
        / MU_O_CP
    )


def self_test() -> None:

    # The AV4 physics axis must be sensitive both to saturation and to
    # the spatial AV3 constitutive parameters.
    sat = np.asarray(
        [
            0.25,
            0.50,
            0.75,
        ],
        dtype=np.float64,
    )

    homogeneous = av3_spatial_mobility(
        sat,
        np.full(
            3,
            3.0,
        ),
        np.full(
            3,
            3.0,
        ),
        np.full(
            3,
            0.80,
        ),
        np.full(
            3,
            0.80,
        ),
    )

    heterogeneous = av3_spatial_mobility(
        sat,
        np.asarray(
            [
                2.2,
                3.0,
                3.8,
            ]
        ),
        np.asarray(
            [
                3.8,
                3.0,
                2.2,
            ]
        ),
        np.asarray(
            [
                0.65,
                0.80,
                0.95,
            ]
        ),
        np.asarray(
            [
                0.95,
                0.80,
                0.65,
            ]
        ),
    )

    if not np.all(
        np.isfinite(
            homogeneous
        )
    ):
        raise RuntimeError("homogeneous_mobility_nonfinite")

    if not np.all(
        np.isfinite(
            heterogeneous
        )
    ):
        raise RuntimeError("heterogeneous_mobility_nonfinite")

    if np.array_equal(
        homogeneous,
        heterogeneous,
    ):
        raise RuntimeError("spatial_constitutive_feedback_not_exposed")

    if np.allclose(
        heterogeneous,
        heterogeneous[
            0
        ],
    ):
        raise RuntimeError("saturation_dependence_not_exposed")

    print(
        "POSTV16-AV4-A0 dynamic-flow authority-gap/physics-impact self-test: PASS"
    )


def main(
    root: Path,
    drive: Path,
) -> int:

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:

        ok = bool(
            passed
        )

        gates[
            name
        ] = {
            "passed":
                ok,
            "value":
                value,
        }

        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (
                f" — {value}"
                if value is not None
                else ""
            )
        )

        if not ok:
            raise GateError(
                name
            )

    print("=" * 214)
    print(
        "POSTV16-AV4-A0 — DYNAMIC PRESSURE-REFRESH / SATURATION-DEPENDENT "
        "SPATIAL-MOBILITY FEEDBACK AUTHORITY-GAP + PHYSICS-IMPACT FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO PRESSURE SOLVE.")
    print("NO DARCY-FLUX RECOMPUTATION.")
    print("NO POLLOCK RETRACE / TOF RECOMPUTATION.")
    print("NO MODEL INFERENCE / TRAINING / RETUNING.")
    print("NO SAME-TIME EOS RECONCILIATION EXECUTION.")
    print("NO MAPBACK / LP EXECUTION.")
    print("NO CMG.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Exact repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(
            root,
            "rev-parse",
            "HEAD^",
        )

        status = git_text(
            root,
            "status",
            "--porcelain",
        )

        gate(
            "repository_parent_is_AV3F_commit",
            parent
            == PARENT_AV3F_COMMIT,
            parent,
        )

        gate(
            "repository_clean",
            status
            == "",
            repr(
                status
            ),
        )

        for fn, expected in SOURCE_BLOBS.items():

            p = root / fn

            actual = (
                git_text(
                    root,
                    "hash-object",
                    str(
                        p
                    ),
                )
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual
                == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind formal AV3-F authority.
        # ------------------------------------------------------------------------------------------
        stage = "AV3F_authority_binding"

        av3f_dir = drive / AV3F_REL

        gate(
            "AV3F_output_present",
            av3f_dir.is_dir(),
            str(
                av3f_dir
            ),
        )

        av3f_manifest = verify_manifest(
            av3f_dir,
            AV3F_MANIFEST,
        )

        gate(
            "AV3F_manifest_exact_9",
            len(
                av3f_manifest
            )
            == 9,
            len(
                av3f_manifest
            ),
        )

        av3f_summary = load_json(
            av3f_dir
            / AV3F_SUMMARY
        )

        av3f_claims = load_json(
            av3f_dir
            / AV3F_CLAIMS
        )

        av3f_handoff = load_json(
            av3f_dir
            / AV3F_HANDOFF
        )

        av3f_decision = load_json(
            av3f_dir
            / AV3F_DECISION
        )

        gate(
            "AV3F_status_exact",
            av3f_summary[
                "status"
            ]
            == AV3F_STATUS,
            av3f_summary[
                "status"
            ],
        )

        gate(
            "AV3F_checkpoint_exact",
            av3f_summary[
                "checkpoint_sha256"
            ]
            == CHECKPOINT_SHA
            and int(
                av3f_summary[
                    "checkpoint_best_epoch"
                ]
            )
            == BEST_EPOCH,
        )

        gate(
            "AV3F_4x9x36_exact",
            int(
                av3f_summary[
                    "AV3_realizations"
                ]
            )
            == AV3_REALIZATIONS
            and int(
                av3f_summary[
                    "canonical_times"
                ]
            )
            == AV3_CANONICAL_TIMES
            and int(
                av3f_summary[
                    "frozen_integrated_states"
                ]
            )
            == AV3_INTEGRATED_STATES,
        )

        gate(
            "AV3F_internal_complete_external_CMG_deferred",
            av3f_decision[
                "AV3_internal_system_development_complete"
            ]
            is True
            and av3f_decision[
                "AV3_external_validation_complete"
            ]
            is False
            and av3f_decision[
                "CMG_validation_performed"
            ]
            is False,
        )

        gate(
            "AV3F_AV4_A0_authorized_only",
            av3f_handoff[
                "AV4_authorized"
            ]
            is True
            and av3f_handoff[
                "next"
            ][
                "milestone"
            ]
            == MILESTONE
            and av3f_handoff[
                "next"
            ][
                "authorized"
            ]
            is True
            and av3f_handoff[
                "next"
            ][
                "execution"
            ]
            is False,
        )

        gate(
            "AV3F_checkpoint_not_automatic_AV4_authority",
            av3f_handoff[
                "AV4_initial_scope"
            ][
                "AV3_checkpoint_may_be_assumed_authoritative_for_AV4"
            ]
            is False,
        )

        gate(
            "AV3F_CMG_cannot_guide_AV4_design",
            av3f_handoff[
                "AV4_initial_scope"
            ][
                "external_CMG_may_guide_AV4_design"
            ]
            is False,
        )

        # ------------------------------------------------------------------------------------------
        # Source-level authority-gap evidence.
        # ------------------------------------------------------------------------------------------
        stage = "source_level_gap_binding"

        sg3_text = (
            root
            / SG3
        ).read_text(
            encoding="utf-8"
        )

        r3r2r1_text = (
            root
            / R3R2R1
        ).read_text(
            encoding="utf-8"
        )

        r3r3_text = (
            root
            / R3R3
        ).read_text(
            encoding="utf-8"
        )

        r3r3r1_text = (
            root
            / R3R3R1
        ).read_text(
            encoding="utf-8"
        )

        gate(
            "SG3_reference_mobility_pressure_solve_exact",
            "MU_REF_CP = 0.50"
            in sg3_text
            and "steady reference-mobility pressure equation"
            in sg3_text,
        )

        gate(
            "historical_refresh_homogeneous_Corey_exact",
            "kr_inj = KR_INJECTED_ENDPOINT * Se**2.0"
            in r3r2r1_text
            and "kr_res = KR_RESIDENT_ENDPOINT * (1.0 - Se) ** 2.0"
            in r3r2r1_text
            and "KR_INJECTED_ENDPOINT = 0.80"
            in r3r2r1_text
            and "KR_RESIDENT_ENDPOINT = 0.80"
            in r3r2r1_text,
        )

        gate(
            "historical_refresh_total_mobility_pressure_link_present",
            "lam_t = lam_inj + lam_res"
            in r3r2r1_text
            and "lambda_total"
            in r3r2r1_text
            and "build_updated_transmissibilities"
            in r3r2r1_text
            and "assemble_updated_pressure_system"
            in r3r2r1_text,
        )

        gate(
            "historical_refresh_rebuilds_flow_kinematics",
            "CONSERVATIVE_DARCY_FACE_FLUXES"
            in r3r3_text
            and "EXACT_POLLOCK_RETRACE"
            in r3r3_text
            and "TOF_RECONSTRUCTION"
            in r3r3_text
            and "EXACT_SG7D_OVERLAP_REBUILD"
            in r3r3_text,
        )

        gate(
            "historical_mass_conservative_same_time_reconciliation_present",
            "cellwise Cartesian CO2 component mass array"
            in r3r3r1_text
            and "FINITE_VOLUME_PRESSURE_SOLVE"
            in r3r3r1_text
            and "EOS_INVERT_FIXED_MASS_TO_RECONCILED_SATURATION"
            in r3r3r1_text
            and "PRESSURE_SATURATION_CONVERGENCE_CHECK"
            in r3r3r1_text,
        )

        # ------------------------------------------------------------------------------------------
        # AV4-A0 authority gap.
        # ------------------------------------------------------------------------------------------
        stage = "authority_gap_freeze"

        authority_gap = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "AV3_frozen_state": {
                "spatial_constitutive_parameters": [
                    "nw(x)",
                    "no(x)",
                    "krw_max(x)",
                    "kro_max(x)",
                ],

                "porosity":
                    "paired AV2 spatial porosity realization",

                "pressure_Darcy_Pollock_TOF":
                    (
                        "held frozen within AV3 and inherited from the paired "
                        "AV2 flow/kinematics authority"
                    ),

                "checkpoint_sha256":
                    CHECKPOINT_SHA,

                "checkpoint_best_epoch":
                    BEST_EPOCH,

                "integrated_states":
                    36,
            },

            "authority_gap": [
                {
                    "id":
                        "AV4_GAP_1_REFERENCE_MOBILITY_PRESSURE",

                    "gap":
                        (
                            "The frozen SG3/AV2/AV3 pressure field is a reference-mobility "
                            "pressure solution and is not a solution of the evolving AV3 "
                            "spatial total-mobility field."
                        ),
                },
                {
                    "id":
                        "AV4_GAP_2_SPATIAL_RELATIVE_PERMEABILITY_FEEDBACK",

                    "gap":
                        (
                            "AV3's spatial nw/no/krw_max/kro_max fields affect transport "
                            "but were not allowed to feed back into pressure transmissibility, "
                            "producer well mobility, or Darcy flux."
                        ),
                },
                {
                    "id":
                        "AV4_GAP_3_DYNAMIC_STREAMLINE_GEOMETRY",

                    "gap":
                        (
                            "Because Q changes when pressure/mobility change, Pollock "
                            "streamline geometry, streamline weights, TOF, SG7D overlap, "
                            "and E37A control-volume geometry are no longer state-invariant."
                        ),
                },
                {
                    "id":
                        "AV4_GAP_4_PRESSURE_DEPENDENT_EOS_STATE_REPRESENTATION",

                    "gap":
                        (
                            "A same-time pressure refresh changes gas density under the frozen "
                            "EOS. Holding both cellwise component mass and saturation numerically "
                            "fixed would generally violate inventory consistency."
                        ),
                },
                {
                    "id":
                        "AV4_GAP_5_AV3_CHECKPOINT_DOMAIN_SHIFT",

                    "gap":
                        (
                            "The AV3 13-channel checkpoint was trained/validated with frozen "
                            "flow/TOF/pressure conditioning. Its authority does not automatically "
                            "extend to recurrently refreshed pressure/TOF channel trajectories."
                        ),
                },
            ],

            "historical_V16_refresh_architecture_role":
                "STRUCTURAL_PRECEDENT_ONLY_NOT_AV4_SPATIAL_CONSTITUTIVE_AUTHORITY",

            "reason":
                (
                    "The historical refresh implementation used fixed exponent 2 and "
                    "fixed relperm endpoints 0.80/0.80, while AV4 inherits spatially "
                    "heterogeneous AV3 constitutive fields."
                ),
        }

        gate(
            "authority_gap_exactly_5",
            len(
                authority_gap[
                    "authority_gap"
                ]
            )
            == 5,
            len(
                authority_gap[
                    "authority_gap"
                ]
            ),
        )

        # ------------------------------------------------------------------------------------------
        # AV4 governing dependency graph.
        # ------------------------------------------------------------------------------------------

        coupling = {
            "transport_state_variable":
                "S(x,t) in the frozen AV3 [0.20,0.80] saturation convention",

            "effective_saturation":
                "Se = clip((S-Swc)/(1-Swc-Sor),0,1)",

            "fixed_residual_saturations": {
                "Swc":
                    SWC,
                "Sor":
                    SOR,
                "span":
                    SPAN,
            },

            "spatial_relative_permeability": {
                "krw":
                    "krw_max(x) * Se**nw(x)",

                "kro":
                    "kro_max(x) * (1-Se)**no(x)",

                "nw_range":
                    list(
                        NW_RANGE
                    ),

                "no_range":
                    list(
                        NO_RANGE
                    ),

                "krw_max_range":
                    list(
                        KRW_MAX_RANGE
                    ),

                "kro_max_range":
                    list(
                        KRO_MAX_RANGE
                    ),
            },

            "phase_mobility": {
                "lambda_w":
                    "krw/mu_w",

                "lambda_o":
                    "kro/mu_o",

                "mu_w_cp":
                    MU_W_CP,

                "mu_o_cp":
                    MU_O_CP,

                "lambda_total":
                    "lambda_w + lambda_o",
            },

            "required_dependency_chain": [
                "accepted or same-time reconciled Cartesian saturation",
                "spatial AV3 Corey/relperm fields",
                "cell total mobility lambda_t(x,S)",
                "face mobility operator",
                "mobility-updated finite-volume pressure system",
                "mobility-updated producer well indices",
                "converged pressure",
                "conservative Darcy face fluxes",
                "exact Pollock streamline retrace and new weights",
                "new physical TOF / normalized transport coordinates",
                "new SG7D overlap and E37A control-volume geometry",
                "reconstructed PI-RNN predictor channels",
                "transport update",
                "conservative mapback / local-PV EOS state update",
            ],

            "same_time_pressure_refresh_inventory_rule":
                (
                    "Cellwise Cartesian component mass is the primary conserved quantity "
                    "during a pressure-only refresh. If pressure changes EOS density, "
                    "saturation may require same-time thermodynamic reconciliation before "
                    "the flow epoch is committed."
                ),

            "refresh_is_transport_transition":
                False,

            "refresh_advances_physical_time":
                False,

            "refresh_changes_cumulative_injection_production_ledgers":
                False,
        }

        gate(
            "spatial_mobility_equation_complete",
            coupling[
                "phase_mobility"
            ][
                "lambda_total"
            ]
            == "lambda_w + lambda_o"
            and len(
                coupling[
                    "required_dependency_chain"
                ]
            )
            >= 12,
        )

        # ------------------------------------------------------------------------------------------
        # Physics-impact / authority classification.
        # ------------------------------------------------------------------------------------------

        impact_rows = [
            {
                "quantity":
                    "spatial porosity phi(x)",

                "AV3_status":
                    "FROZEN_AUTHORITY",

                "AV4_status":
                    "REUSE_UNCHANGED",

                "reason":
                    "AV4 dynamic-flow axis does not redefine the AV2/AV3 porosity model.",
            },
            {
                "quantity":
                    "spatial nw/no/krw_max/kro_max",

                "AV3_status":
                    "FROZEN_AUTHORITY",

                "AV4_status":
                    "REUSE_AS_MOBILITY_INPUT",

                "reason":
                    "These frozen fields now drive both transport and total mobility.",
            },
            {
                "quantity":
                    "pressure",

                "AV3_status":
                    "FROZEN_PER_REALIZATION",

                "AV4_status":
                    "DYNAMIC_RECOMPUTATION_REQUIRED",

                "reason":
                    "Pressure operator depends on evolving total mobility.",
            },
            {
                "quantity":
                    "Darcy Qx/Qy/Qz",

                "AV3_status":
                    "FROZEN_PER_REALIZATION",

                "AV4_status":
                    "DYNAMIC_RECOMPUTATION_REQUIRED",

                "reason":
                    "Flux depends on updated pressure and mobility-scaled transmissibility.",
            },
            {
                "quantity":
                    "Pollock streamlines / weights",

                "AV3_status":
                    "FROZEN_PER_REALIZATION",

                "AV4_status":
                    "DYNAMIC_RETRACE_REQUIRED",

                "reason":
                    "Velocity topology and injector outflow weights change with Q.",
            },
            {
                "quantity":
                    "TOF / eta / geometry channels",

                "AV3_status":
                    "FROZEN_PER_REALIZATION",

                "AV4_status":
                    "DYNAMIC_RECOMPUTATION_REQUIRED",

                "reason":
                    "TOF and normalized transport coordinates depend on refreshed velocity.",
            },
            {
                "quantity":
                    "SG7D / E37A transfer geometry",

                "AV3_status":
                    "FROZEN_PER_REALIZATION",

                "AV4_status":
                    "DYNAMIC_REBUILD_REQUIRED",

                "reason":
                    "Cell crossings and CV geometry depend on refreshed streamline paths.",
            },
            {
                "quantity":
                    "AV3 epoch-92 checkpoint",

                "AV3_status":
                    "FINAL_AV3_TRANSPORT_AUTHORITY",

                "AV4_status":
                    "NOT_AUTOMATIC_AUTHORITY",

                "reason":
                    (
                        "Dynamic pressure/TOF channel trajectories create a new deployment "
                        "domain that requires explicit compatibility/validation."
                    ),
            },
            {
                "quantity":
                    "B1 / conservative mapback / local-PV / R7D terminal halo",

                "AV3_status":
                    "FROZEN_CONSERVATIVE_ARCHITECTURE",

                "AV4_status":
                    "PRESERVE_UNLESS_EXPLICITLY_INVALIDATED",

                "reason":
                    (
                        "AV4 changes upstream flow/kinematics; no authority currently exists "
                        "to alter downstream conservation semantics."
                    ),
            },
        ]

        gate(
            "physics_impact_registry_complete",
            len(
                impact_rows
            )
            == 9,
            len(
                impact_rows
            ),
        )

        # ------------------------------------------------------------------------------------------
        # A0 deliberately does NOT freeze implementation choices that need a dedicated A1.
        # ------------------------------------------------------------------------------------------

        unresolved = {
            "must_be_frozen_in_AV4_A1": [
                "cell-to-face total-mobility averaging rule",
                "mobility scaling of anisotropic transmissibility",
                "producer well-index mobility scaling",
                "gravity-density policy under two-phase refresh",
                "same-time pressure/saturation fixed-point iteration",
                "pressure convergence tolerance",
                "saturation reconciliation convergence tolerance",
                "maximum refresh iteration count",
                "capacity policy during same-time EOS reconciliation",
                "exact refreshed-flow validation gates",
                "flow-epoch commit/rollback semantics",
                "hard refresh triggers",
                "production refresh cadence policy",
                "13-channel reconstruction under refreshed geometry",
                "AV3 checkpoint compatibility test versus retraining trigger",
            ],

            "not_selected_in_A0": {
                "face_mobility_rule":
                    None,

                "pressure_tolerance":
                    None,

                "saturation_tolerance":
                    None,

                "maximum_fixed_point_iterations":
                    None,

                "production_refresh_cadence":
                    None,

                "checkpoint_reuse":
                    None,
            },

            "historical_candidates_not_yet_promoted": {
                "face_mobility":
                    "harmonic total mobility from V16E41-R3-R2-R1",

                "same_time_reconciliation":
                    (
                        "cellwise-mass-conservative direct Picard architecture "
                        "from V16E41-R3-R3-R1"
                    ),

                "flow_epoch_state_machine":
                    "V16E41-R3-R3 structural precedent",
            },
        }

        gate(
            "A0_does_not_prematurely_select_A1_parameters",
            all(
                value
                is None
                for value in unresolved[
                    "not_selected_in_A0"
                ].values()
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Explicit scientific boundaries.
        # ------------------------------------------------------------------------------------------

        boundaries = {
            "A0_execution": {
                "pressure_solve":
                    False,

                "Darcy_flux_recompute":
                    False,

                "Pollock_retrace":
                    False,

                "TOF_recompute":
                    False,

                "model_inference":
                    False,

                "training":
                    False,

                "same_time_EOS_reconciliation":
                    False,

                "mapback":
                    False,

                "LP":
                    False,

                "CMG":
                    False,
            },

            "claims_not_authorized": [
                "AV4 improves pressure accuracy",
                "AV4 improves plume accuracy",
                "AV3 checkpoint remains accurate after dynamic-flow refresh",
                "historical homogeneous-mobility refresh metrics transfer to AV4",
                "a production refresh cadence is known",
                "a face-mobility rule has been scientifically selected for AV4",
                "external CMG validates AV4",
                "AV4 has passed any dynamic-flow execution",
            ],

            "external_validation_firewall":
                (
                    "External CMG/full-physics results remain deferred and may not guide "
                    "AV4-A0/A1 design or parameter selection."
                ),
        }

        # ------------------------------------------------------------------------------------------
        # Next milestone.
        # ------------------------------------------------------------------------------------------

        handoff = {
            "milestone":
                "POSTV16-AV4-A1",

            "name":
                (
                    "Spatial Total-Mobility / Pressure-Refresh Operator, "
                    "Mass-Conservative Same-Time Reconciliation, and Flow-Epoch Contract Freeze"
                ),

            "authorized":
                True,

            "execution":
                False,

            "required": [
                "bind exact AV3 spatial constitutive field authority",
                "freeze exact cell-to-face mobility rule",
                "freeze mobility-updated pressure transmissibility and producer well-index algebra",
                "freeze gravity-density policy",
                "freeze mass-conservative same-time pressure/saturation reconciliation",
                "freeze convergence tolerances and maximum iterations prospectively",
                "freeze pressure/Q/Pollock/TOF/overlap validation gates",
                "freeze 13-channel reconstruction after a flow refresh",
                "freeze checkpoint compatibility-vs-retraining decision protocol",
                "freeze refresh trigger/state-machine semantics without selecting production cadence from CMG",
            ],

            "AV4_dynamic_flow_execution_authorized":
                False,
        }

        decision = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "AV3F_authority_bound":
                True,

            "AV3_checkpoint_sha256":
                CHECKPOINT_SHA,

            "AV3_checkpoint_best_epoch":
                BEST_EPOCH,

            "authority_gap_frozen":
                True,

            "spatial_total_mobility_physics_axis_frozen":
                True,

            "pressure_dynamic_dependency_frozen":
                True,

            "Darcy_dynamic_dependency_frozen":
                True,

            "Pollock_TOF_dynamic_dependency_frozen":
                True,

            "same_time_component_mass_conservation_requirement_frozen":
                True,

            "historical_refresh_architecture_is_structural_precedent_only":
                True,

            "AV3_checkpoint_automatic_AV4_authority":
                False,

            "face_mobility_rule_selected":
                False,

            "fixed_point_tolerances_selected":
                False,

            "refresh_cadence_selected":
                False,

            "pressure_solve_performed":
                False,

            "Darcy_flux_recomputed":
                False,

            "Pollock_retrace_performed":
                False,

            "TOF_recomputed":
                False,

            "model_inference_performed":
                False,

            "training_performed":
                False,

            "CMG_validation_performed":
                False,

            "AV4_A1_authorized":
                True,

            "AV4_dynamic_flow_execution_authorized":
                False,

            "next":
                handoff,
        }

        summary = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "AV3_checkpoint_sha256":
                CHECKPOINT_SHA,

            "AV3_checkpoint_best_epoch":
                BEST_EPOCH,

            "AV3_realizations":
                AV3_REALIZATIONS,

            "AV3_integrated_states":
                AV3_INTEGRATED_STATES,

            "authority_gaps":
                len(
                    authority_gap[
                        "authority_gap"
                    ]
                ),

            "physics_impact_quantities":
                len(
                    impact_rows
                ),

            "A1_unresolved_items":
                len(
                    unresolved[
                        "must_be_frozen_in_AV4_A1"
                    ]
                ),

            "pressure_solve":
                False,

            "model_inference":
                False,

            "CMG":
                False,

            "AV4_A1_authorized":
                True,

            "AV4_dynamic_flow_execution_authorized":
                False,

            "next":
                handoff,
        }

        artifacts = {
            "PAD_Stream_POSTV16_AV4_A0_Summary.json":
                json_bytes(
                    summary
                ),

            "POSTV16_AV4_A0_Authority_Gap_Registry.json":
                json_bytes(
                    authority_gap
                ),

            "POSTV16_AV4_A0_Spatial_Mobility_and_Dynamic_Flow_Dependency_Contract.json":
                json_bytes(
                    coupling
                ),

            "POSTV16_AV4_A0_Physics_Impact_Authority_Registry.csv":
                csv_bytes(
                    impact_rows
                ),

            "POSTV16_AV4_A0_Unresolved_A1_Design_Registry.json":
                json_bytes(
                    unresolved
                ),

            "POSTV16_AV4_A0_Scientific_Boundaries.json":
                json_bytes(
                    boundaries
                ),

            "POSTV16_AV4_A0_A1_Handoff_Contract.json":
                json_bytes(
                    handoff
                ),

            "POSTV16_AV4_A0_Decision_Contract.json":
                json_bytes(
                    decision
                ),

            "POSTV16_AV4_A0_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {
                            "gate":
                                key,
                            **value,
                        }
                        for key, value in gates.items()
                    ]
                ),
        }

        immutable_publish(
            out,
            artifacts,
        )

        manifest_rows = []

        for q in sorted(
            out.iterdir()
        ):

            if (
                q.is_file()
                and q.name
                != "POSTV16_AV4_A0_Artifact_Manifest.csv"
            ):

                manifest_rows.append(
                    {
                        "file":
                            q.name,

                        "sha256":
                            sha256_file(
                                q
                            ),

                        "bytes":
                            q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_A0_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A0: AUTHORITY-GAP / PHYSICS-IMPACT FREEZE PASS")
        print("=" * 214)
        print("AV3 final authority                       : BOUND")
        print("AV3 checkpoint                            : epoch 92")
        print("Checkpoint SHA256                         :", CHECKPOINT_SHA)
        print("AV4 authority gaps                        : 5")
        print("AV4 physics-impact quantities             : 9")
        print("Spatial AV3 total-mobility feedback       : REQUIRED")
        print("Pressure/Q/Pollock/TOF dynamic dependency : FROZEN")
        print("Same-time component-mass conservation     : REQUIRED")
        print("Historical V16 refresh architecture       : STRUCTURAL PRECEDENT ONLY")
        print("AV3 checkpoint automatic AV4 authority    : False")
        print("Face-mobility rule selected in A0         : False")
        print("Fixed-point tolerances selected in A0     : False")
        print("Production refresh cadence selected       : False")
        print("Pressure/flow execution in A0             : False")
        print("CMG                                        : Deferred")
        print("POSTV16-AV4-A1                            : AUTHORIZED")
        print("AV4 dynamic-flow execution                : NOT YET AUTHORIZED")
        print("=" * 214)

        return 0

    except Exception as exc:

        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_BLOCKED,

            "failed_stage":
                stage,

            "exception":
                repr(
                    exc
                ),

            "gates":
                gates,

            "pressure_solve_performed":
                False,

            "Darcy_flux_recomputed":
                False,

            "Pollock_retrace_performed":
                False,

            "TOF_recomputed":
                False,

            "model_inference_performed":
                False,

            "training_performed":
                False,

            "CMG_validation_performed":
                False,

            "AV4_A1_authorized":
                False,

            "AV4_dynamic_flow_execution_authorized":
                False,
        }

        p = (
            blocked
            / "POSTV16_AV4_A0_Blocked_Report.json"
        )

        if not p.exists():
            p.write_bytes(
                json_bytes(
                    report
                )
            )

        print()
        print("POSTV16-AV4-A0: BLOCKED")
        print("Stage    :", stage)
        print("Exception:", repr(exc))

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
        raise SystemExit(
            0
        )

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
