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


MILESTONE = "POSTV16-AV4-A1"

PROTOCOL_ID = (
    "POSTV16_AV4_A1_SPATIAL_TOTAL_MOBILITY_PRESSURE_REFRESH_"
    "MASS_CONSERVATIVE_SAME_TIME_RECONCILIATION_FLOW_EPOCH_V1"
)

STATUS_PASS = (
    "AV4A1_SPATIAL_TOTAL_MOBILITY_PRESSURE_REFRESH_OPERATOR_MASS_CONSERVATIVE_"
    "SAME_TIME_RECONCILIATION_AND_FLOW_EPOCH_CONTRACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

STATUS_BLOCKED = "AV4A1_DYNAMIC_FLOW_OPERATOR_CONTRACT_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_A0_COMMIT = "3750a20f79c22ecdb6e1a5b9a4606454b03f3c6a"

A0_STATUS = (
    "AV4A0_DYNAMIC_PRESSURE_REFRESH_SATURATION_DEPENDENT_SPATIAL_MOBILITY_"
    "FEEDBACK_AUTHORITY_GAP_AND_PHYSICS_IMPACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

CHECKPOINT_SHA = (
    "17b188494e0452570d43e868c20c4c814e6a1f0b493329d0e40849c4c5ec6d4e"
)

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

A0 = "PAD_Stream_POSTV16_AV4_A0_Dynamic_Flow_Authority_Gap_and_Physics_Impact_Freeze.py"
A0_BLOB = "e52474e9e172a3e29af3851072c6adfb76250384"

AV3F = (
    "PAD_Stream_POSTV16_AV3_F_"
    "Final_Spatial_Corey_Relperm_Outcome_Freeze_and_AV4_Handoff.py"
)
AV3F_BLOB = "4a24a0646048be58b9abebf113d87a165692c916"

AV3A2 = (
    "PAD_Stream_POSTV16_AV3_A2_"
    "Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling.py"
)
AV3A2_BLOB = "e7d4f1b1e69ea3e756c4f41d7edb57e2ffd87d7b"

AV3A3R1 = (
    "PAD_Stream_POSTV16_AV3_A3_R1_"
    "First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
)
AV3A3R1_BLOB = "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49"

AV3A6E = (
    "PAD_Stream_POSTV16_AV3_A6_E_"
    "Frozen_Checkpoint_LocalPV_R7D_Integration_Execution.py"
)
AV3A6E_BLOB = "e3dcb0aa9354c399904f7f0e830b6a1fddd78987"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

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

R3R4 = (
    "PAD_Stream_V16E41R3R4_"
    "Controlled_Same_Parent_Mass_Conservative_Refreshed_Flow_Transition_Validation.py"
)
R3R4_BLOB = "c4fdaf1e5886e2ba2618636406d63aa190152856"

SOURCE_BLOBS = {
    A0: A0_BLOB,
    AV3F: AV3F_BLOB,
    AV3A2: AV3A2_BLOB,
    AV3A3R1: AV3A3R1_BLOB,
    AV3A6E: AV3A6E_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    R2: R2_BLOB,
    R3R2R1: R3R2R1_BLOB,
    R3R3: R3R3_BLOB,
    R3R3R1: R3R3R1_BLOB,
    R3R4: R3R4_BLOB,
}

# --------------------------------------------------------------------------------------------------
# A0 Drive authority.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV4_Dynamic_Flow_Coupling"
)

A0_REL = (
    BASE_AV4
    / "POSTV16_AV4_A0_Dynamic_Flow_Authority_Gap_and_Physics_Impact_Freeze"
)

A0_SUMMARY = "PAD_Stream_POSTV16_AV4_A0_Summary.json"
A0_COUPLING = "POSTV16_AV4_A0_Spatial_Mobility_and_Dynamic_Flow_Dependency_Contract.json"
A0_UNRESOLVED = "POSTV16_AV4_A0_Unresolved_A1_Design_Registry.json"
A0_DECISION = "POSTV16_AV4_A0_Decision_Contract.json"
A0_MANIFEST = "POSTV16_AV4_A0_Artifact_Manifest.csv"

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_A1_Spatial_Mobility_Pressure_Refresh_and_Flow_Epoch_Contract_Freeze"
)

BLOCK_REL = BASE_AV4 / "POSTV16_AV4_A1_BLOCKED"

# --------------------------------------------------------------------------------------------------
# Prospectively selected A1 constants.
# --------------------------------------------------------------------------------------------------

SWC = 0.20
SOR = 0.20
SPAN = 0.60

MU_W_PA_S = 0.50e-3
MU_O_PA_S = 5.00e-3

REFERENCE_MU_PA_S = 0.50e-3
REFERENCE_MOBILITY = 1.0 / REFERENCE_MU_PA_S

FACE_MOBILITY_RULE = "HARMONIC_TOTAL_MOBILITY"

GRAVITY_DENSITY_POLICY = (
    "SG3_REFERENCE_BRINE_DENSITY_1020_KG_M3_HELD_FIXED_"
    "TO_ISOLATE_SPATIAL_TOTAL_MOBILITY_FEEDBACK"
)

RHO_GRAVITY_KG_M3 = 1020.0

MAX_FIXED_POINT_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8

FLOW_LOCAL_REL_L2_MAX = 1.0e-8
FLOW_GLOBAL_REL_MISMATCH_MAX = 1.0e-8
INJECTOR_WEIGHT_REL_CLOSURE_MAX = 1.0e-10

CELL_MASS_ABS_FLOOR_KG = 1.0e-8
CELL_MASS_REL_TOL = 1.0e-10
GLOBAL_MASS_REL_TOL = 1.0e-10

A2_CONTROL_REALIZATION = "AV3CR0003"
A2_CONTROL_POROSITY = "AV2PHI0003"
A2_CONTROL_PARTITION = "VALIDATION"
A2_CONTROL_DAY = 365.0


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


def spatial_total_mobility(
    saturation: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
) -> np.ndarray:

    S = np.asarray(saturation, dtype=np.float64)

    Se = np.clip(
        (S - SWC) / SPAN,
        0.0,
        1.0,
    )

    krw = np.asarray(krw_max, dtype=np.float64) * Se ** np.asarray(nw, dtype=np.float64)

    kro = np.asarray(kro_max, dtype=np.float64) * (1.0 - Se) ** np.asarray(no, dtype=np.float64)

    lam = krw / MU_W_PA_S + kro / MU_O_PA_S

    if not np.all(np.isfinite(lam)) or np.any(lam <= 0.0):
        raise GateError("invalid_spatial_total_mobility")

    return lam


def harmonic_positive(a: np.ndarray, b: np.ndarray) -> np.ndarray:

    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)

    denom = aa + bb

    if np.any(denom <= 0.0):
        raise GateError("nonpositive_harmonic_denominator")

    return 2.0 * aa * bb / denom


def relative_l2(new: np.ndarray, old: np.ndarray) -> float:

    a = np.asarray(new, dtype=np.float64)
    b = np.asarray(old, dtype=np.float64)

    return float(
        np.linalg.norm((a - b).ravel())
        / max(
            float(np.linalg.norm(b.ravel())),
            1.0e-30,
        )
    )


def self_test() -> None:

    S = np.asarray([0.25, 0.50, 0.75], dtype=np.float64)

    lam = spatial_total_mobility(
        S,
        np.asarray([2.2, 3.0, 3.8]),
        np.asarray([3.8, 3.0, 2.2]),
        np.asarray([0.65, 0.80, 0.95]),
        np.asarray([0.95, 0.80, 0.65]),
    )

    if not np.all(lam > 0.0):
        raise RuntimeError("mobility_nonpositive")

    hf = harmonic_positive(
        lam[:-1],
        lam[1:],
    )

    if not np.all(hf > 0.0):
        raise RuntimeError("face_mobility_nonpositive")

    if not (
        MAX_FIXED_POINT_ITERATIONS == 100
        and PRESSURE_REL_L2_TOL == 1.0e-10
        and SATURATION_LINF_TOL == 1.0e-10
        and PRESSURE_LINEAR_REL_RESIDUAL_MAX == 1.0e-8
    ):
        raise RuntimeError("fixed_point_contract")

    if A2_CONTROL_PARTITION != "VALIDATION":
        raise RuntimeError("A2_control_must_not_be_train_or_locked_OOD")

    print(
        "POSTV16-AV4-A1 spatial-mobility pressure-refresh/flow-epoch contract self-test: PASS"
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

    print("=" * 214)
    print(
        "POSTV16-AV4-A1 — SPATIAL TOTAL-MOBILITY / PRESSURE-REFRESH OPERATOR / "
        "MASS-CONSERVATIVE SAME-TIME RECONCILIATION / FLOW-EPOCH CONTRACT FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO PRESSURE SOLVE / DARCY-FLUX RECOMPUTATION.")
    print("NO POLLOCK RETRACE / TOF REBUILD.")
    print("NO PI-RNN INFERENCE / TRAINING.")
    print("NO EOS FIXED-POINT EXECUTION.")
    print("NO MAPBACK / LP.")
    print("NO CMG.")
    print()

    try:

        # ------------------------------------------------------------------------------------------
        # Exact repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_A0_commit",
            parent == PARENT_A0_COMMIT,
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
                git_text(root, "hash-object", str(p))
                if p.is_file()
                else "missing"
            )

            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind canonical AV4-A0 PASS.
        # ------------------------------------------------------------------------------------------
        stage = "A0_authority_binding"

        a0dir = drive / A0_REL

        gate(
            "A0_output_present",
            a0dir.is_dir(),
            str(a0dir),
        )

        a0_manifest = verify_manifest(
            a0dir,
            A0_MANIFEST,
        )

        gate(
            "A0_manifest_exact_9",
            len(a0_manifest) == 9,
            len(a0_manifest),
        )

        a0_summary = load_json(a0dir / A0_SUMMARY)
        a0_coupling = load_json(a0dir / A0_COUPLING)
        a0_unresolved = load_json(a0dir / A0_UNRESOLVED)
        a0_decision = load_json(a0dir / A0_DECISION)

        gate(
            "A0_status_exact",
            a0_summary["status"] == A0_STATUS,
            a0_summary["status"],
        )

        gate(
            "A0_14_stage_dependency_chain_exact",
            len(
                a0_coupling[
                    "required_dependency_chain"
                ]
            )
            == 14,
            len(
                a0_coupling[
                    "required_dependency_chain"
                ]
            ),
        )

        gate(
            "A0_A1_authorized_dynamic_execution_false",
            a0_decision[
                "AV4_A1_authorized"
            ]
            is True
            and a0_decision[
                "AV4_dynamic_flow_execution_authorized"
            ]
            is False,
        )

        gate(
            "A0_checkpoint_not_automatic_AV4_authority",
            a0_decision[
                "AV3_checkpoint_automatic_AV4_authority"
            ]
            is False,
        )

        gate(
            "A0_design_choices_were_unselected",
            all(
                value is None
                for value in a0_unresolved[
                    "not_selected_in_A0"
                ].values()
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Bind historical internal numerical candidates at source level.
        # They are evidence/candidates, not automatic authority.
        # ------------------------------------------------------------------------------------------
        stage = "historical_candidate_binding"

        r3r2_text = (root / R3R2R1).read_text(encoding="utf-8")
        r3r3r1_text = (root / R3R3R1).read_text(encoding="utf-8")
        r3r4_text = (root / R3R4).read_text(encoding="utf-8")
        sg3_text = (root / SG3).read_text(encoding="utf-8")

        gate(
            "historical_harmonic_face_mobility_present",
            'FACE_MOBILITY_RULE = "HARMONIC_TOTAL_MOBILITY"'
            in r3r2_text
            and "return 2.0 * a * b / denom"
            in r3r2_text,
        )

        gate(
            "historical_transmissibility_mobility_scaling_present",
            "tx_ref * (lam_x / lambda_ref)"
            in r3r2_text
            and "ty_ref * (lam_y / lambda_ref)"
            in r3r2_text
            and "tz_ref * (lam_z / lambda_ref)"
            in r3r2_text,
        )

        gate(
            "historical_producer_WI_mobility_scaling_present",
            "wi = float(wi_ref) * float(lambda_total[k, j, i] / lambda_ref)"
            in r3r2_text,
        )

        gate(
            "historical_fixed_reference_gravity_density_present",
            "SG3_REFERENCE_BRINE_DENSITY_HELD_FIXED_TO_ISOLATE_MOBILITY_FEEDBACK"
            in r3r2_text
            and "RHO_BRINE_KG_M3"
            in r3r2_text,
        )

        gate(
            "historical_direct_Picard_no_hidden_relaxation_present",
            '"direct_Picard_first": True'
            in r3r3r1_text
            and '"hidden_damping_or_relaxation_authorized": False'
            in r3r3r1_text,
        )

        gate(
            "historical_fixed_point_numerics_present",
            "MAX_FIXED_POINT_ITERATIONS = 100"
            in r3r4_text
            and "PRESSURE_REL_L2_TOL = 1.0e-10"
            in r3r4_text
            and "SATURATION_LINF_TOL = 1.0e-10"
            in r3r4_text,
        )

        gate(
            "historical_SG3_reference_viscosity_present",
            "MU_REF_CP = 0.50"
            in sg3_text
            and "MU_REF_PA_S"
            in sg3_text,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze AV4-A1 exact mobility/pressure operator.
        # ------------------------------------------------------------------------------------------
        stage = "operator_contract_freeze"

        mobility_pressure_contract = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,

            "cell_spatial_relative_permeability": {
                "effective_saturation":
                    "Se=clip((S-0.20)/0.60,0,1)",

                "krw":
                    "krw_max(x)*Se**nw(x)",

                "kro":
                    "kro_max(x)*(1-Se)**no(x)",

                "mu_w_Pa_s":
                    MU_W_PA_S,

                "mu_o_Pa_s":
                    MU_O_PA_S,

                "lambda_w":
                    "krw/mu_w",

                "lambda_o":
                    "kro/mu_o",

                "lambda_total":
                    "lambda_w+lambda_o",

                "constitutive_field_authority":
                    "frozen AV3 spatial nw/no/krw_max/kro_max arrays",
            },

            "face_mobility": {
                "rule":
                    FACE_MOBILITY_RULE,

                "formula":
                    "lambda_f=2*lambda_L*lambda_R/(lambda_L+lambda_R)",

                "positive_mobility_required":
                    True,

                "upwind_mobility_not_selected":
                    True,
            },

            "reference_mobility": {
                "mu_ref_Pa_s":
                    REFERENCE_MU_PA_S,

                "lambda_ref":
                    REFERENCE_MOBILITY,

                "source":
                    "frozen SG3 reference-mobility pressure operator",
            },

            "dynamic_transmissibility": {
                "formula":
                    "T_f_dynamic=T_f_SG3_reference*(lambda_f/lambda_ref)",

                "anisotropic_geometry_and_absolute_permeability":
                    "reuse frozen SG2/SG3 authority unchanged",
            },

            "producer_well_index": {
                "formula":
                    "WI_dynamic=WI_SG3_reference*(lambda_total_well_cell/lambda_ref)",

                "producer_BHP":
                    "reuse frozen SG3 2000 psi authority",

                "injector_control":
                    "reuse frozen SG3 fixed-rate injection authority",
            },

            "gravity": {
                "policy":
                    GRAVITY_DENSITY_POLICY,

                "density_kg_m3":
                    RHO_GRAVITY_KG_M3,

                "dynamic_phase_density_gravity_feedback":
                    False,

                "scope_reason":
                    (
                        "AV4 isolates saturation-dependent spatial total-mobility feedback. "
                        "Dynamic mixture-density gravity is outside this AV4 axis."
                    ),
            },

            "pressure_equation":
                (
                    "reuse exact SG3 finite-volume pressure assembly/sign convention with "
                    "dynamic face transmissibilities, dynamic producer WIs, fixed injection rate, "
                    "fixed producer BHP, and fixed reference-brine gravity density"
                ),

            "pressure_linear_relative_residual_max":
                PRESSURE_LINEAR_REL_RESIDUAL_MAX,
        }

        gate(
            "A1_face_mobility_selected_harmonic",
            mobility_pressure_contract[
                "face_mobility"
            ][
                "rule"
            ]
            == "HARMONIC_TOTAL_MOBILITY",
        )

        gate(
            "A1_reference_mobility_exact_2000",
            mobility_pressure_contract[
                "reference_mobility"
            ][
                "lambda_ref"
            ]
            == 2000.0,
            mobility_pressure_contract[
                "reference_mobility"
            ][
                "lambda_ref"
            ],
        )

        # ------------------------------------------------------------------------------------------
        # Freeze same-time mass-conservative pressure/saturation fixed point.
        # ------------------------------------------------------------------------------------------

        reconciliation_contract = {
            "primary_conserved_refresh_quantity":
                "cellwise Cartesian CO2 component mass",

            "parent_mass_definition":
                (
                    "M_i=PV_i*rho_g(S_i_parent,p_i_parent,p_ref)*"
                    "clip(S_i_parent-0.20,0,0.60)"
                ),

            "pore_volume":
                "paired AV2/AV3 local porosity phi_i times physical cell bulk volume",

            "p_ref":
                "frozen parent/reference gas pressure; unchanged during refresh",

            "iteration": [
                "S^(0)=exact accepted parent saturation; p^(0)=exact accepted parent pressure",
                "evaluate spatial lambda_t(S^(n))",
                "harmonically average lambda_t to faces",
                "build mobility-scaled transmissibilities and producer WIs",
                "solve finite-volume pressure p^(n+1)",
                "invert exact frozen parent cellwise component mass under p^(n+1) using frozen R2 EOS to obtain S^(n+1)",
                "evaluate pressure relative-L2 and saturation L-infinity changes",
                "repeat direct Picard until both convergence tolerances pass",
                "perform one final pressure solve + EOS inversion consistency check from converged saturation",
            ],

            "direct_Picard":
                True,

            "under_relaxation":
                False,

            "pressure_relative_L2_definition":
                "||p_new-p_old||_2/max(||p_old||_2,1e-30)",

            "pressure_relative_L2_tolerance":
                PRESSURE_REL_L2_TOL,

            "saturation_Linf_tolerance":
                SATURATION_LINF_TOL,

            "maximum_iterations":
                MAX_FIXED_POINT_ITERATIONS,

            "pressure_linear_relative_residual_max":
                PRESSURE_LINEAR_REL_RESIDUAL_MAX,

            "capacity_policy": {
                "saturation_bounds":
                    [0.20, 0.80],

                "if_fixed_cell_mass_exceeds_new_pressure_local_capacity":
                    "BLOCK",

                "cell_mass_redistribution":
                    False,

                "mass_clipping":
                    False,

                "saturation_ceiling_relaxation":
                    False,

                "R7D_halo_reconciliation_during_same_time_refresh":
                    False,
            },

            "mass_reconstruction_gates": {
                "cellwise_max_abs_error":
                    (
                        "max_cell_abs_error <= max(1e-8 kg, "
                        "1e-10*max(max(parent_cell_mass),1 kg))"
                    ),

                "cell_mass_abs_floor_kg":
                    CELL_MASS_ABS_FLOOR_KG,

                "cell_mass_relative_scale":
                    CELL_MASS_REL_TOL,

                "global_relative_error_max":
                    GLOBAL_MASS_REL_TOL,
            },

            "invariants": {
                "physical_time_unchanged":
                    True,

                "accepted_transport_step_unchanged":
                    True,

                "cumulative_injected_mass_unchanged":
                    True,

                "cumulative_produced_mass_unchanged":
                    True,

                "cellwise_component_mass_unchanged":
                    True,

                "thermodynamic_saturation_change_is_transport":
                    False,
            },

            "failure_semantics":
                (
                    "Any fixed-point nonconvergence, pressure-solve failure, EOS inversion "
                    "failure, local-capacity failure, or mass-reconstruction failure BLOCKS "
                    "the flow epoch. No hidden damping, clipping, redistribution, or fallback."
                ),
        }

        gate(
            "A1_fixed_point_numerics_exact",
            reconciliation_contract[
                "pressure_relative_L2_tolerance"
            ]
            == 1.0e-10
            and reconciliation_contract[
                "saturation_Linf_tolerance"
            ]
            == 1.0e-10
            and reconciliation_contract[
                "maximum_iterations"
            ]
            == 100,
        )

        gate(
            "A1_same_time_cell_mass_primary",
            reconciliation_contract[
                "primary_conserved_refresh_quantity"
            ]
            == "cellwise Cartesian CO2 component mass",
        )

        # ------------------------------------------------------------------------------------------
        # Freeze flow-epoch rebuild and validation gates.
        # ------------------------------------------------------------------------------------------

        flow_epoch_contract = {
            "commit_sequence_after_fixed_point": [
                "converged reconciled saturation",
                "converged pressure",
                "dynamic transmissibilities",
                "dynamic producer well indices",
                "conservative Darcy Qx/Qy/Qz",
                "exact Pollock streamlines and injector weights",
                "physical TOF and normalized transport coordinates",
                "SG7D overlap operator",
                "E37A control-volume geometry",
                "streamline face pressure",
                "reconstructed 13-channel predictor coordinates",
            ],

            "hard_validation_gates": {
                "pressure_linear_relative_residual":
                    "<1e-8",

                "flow_local_relative_L2":
                    "<1e-8",

                "flow_global_relative_mismatch":
                    "<1e-8",

                "face_fluxes_finite":
                    True,

                "streamlines_all_terminal_producer_captured":
                    True,

                "injector_seed_weight_relative_closure":
                    "<=1e-10",

                "TOF_finite_positive_monotone":
                    True,

                "all_four_producers_represented":
                    True,

                "SG7D_E37A_geometry_finite":
                    True,

                "same_time_cellwise_mass_gate":
                    "required",

                "same_time_global_mass_relative_error":
                    "<=1e-10",
            },

            "rollback": {
                "commit_only_if_all_hard_gates_pass":
                    True,

                "partial_new_flow_epoch_persistence":
                    False,

                "accepted_parent_state_remains_immutable_on_failure":
                    True,
            },
        }

        # ------------------------------------------------------------------------------------------
        # Freeze refresh state machine / cadence policy.
        # ------------------------------------------------------------------------------------------

        state_machine = {
            "states": [
                "FLOW_EPOCH_CLEAN",
                "FLOW_EPOCH_DIRTY",
                "REFRESH_IN_PROGRESS",
                "REFRESH_BLOCKED",
            ],

            "mandatory_refresh_triggers": [
                "restart_or_initialization_when_no_consistent_flow_epoch_exists",
                "well_or_control_change",
                "explicit_controlled_validation_request",
                "capacity_or_geometry_preflight_rejection_attributable_to_stale_flow",
            ],

            "after_accepted_transport_that_changes_saturation":
                "FLOW_EPOCH_DIRTY",

            "production_periodic_cadence": {
                "selected_numeric_interval":
                    None,

                "policy":
                    "DEFER_UNTIL_SINGLE_REFRESH_OPERATOR_VALIDATION_PASSES",

                "CMG_may_set_or_tune_cadence":
                    False,
            },

            "A2_controlled_validation": {
                "realization":
                    A2_CONTROL_REALIZATION,

                "paired_porosity":
                    A2_CONTROL_POROSITY,

                "partition":
                    A2_CONTROL_PARTITION,

                "canonical_day":
                    A2_CONTROL_DAY,

                "reason":
                    (
                        "Use the frozen AV3 validation realization rather than a training "
                        "or locked-OOD realization, at a pre-existing intermediate canonical time."
                    ),

                "physical_time_advance":
                    False,

                "transport_step":
                    False,

                "PI_RNN_inference":
                    False,
            },
        }

        gate(
            "A2_control_is_validation_not_train_or_OOD",
            state_machine[
                "A2_controlled_validation"
            ][
                "partition"
            ]
            == "VALIDATION",
        )

        # ------------------------------------------------------------------------------------------
        # Freeze channel reconstruction and checkpoint authority firewall.
        # ------------------------------------------------------------------------------------------

        channel_checkpoint = {
            "13_channel_order": [
                "xi",
                "pollock_tau_hat",
                "adv_tau_hat",
                "log10_Kh",
                "log10_Kz_over_Kh",
                "porosity",
                "pressure_z",
                "target_time_hat",
                "target_eta_sequence",
                "nw_hat",
                "no_hat",
                "krw_max_hat",
                "kro_max_hat",
            ],

            "refreshed_geometry_effects": {
                "xi":
                    "common normalized 201-node coordinate retained",

                "pollock_tau_hat":
                    "recompute from refreshed Pollock/TOF",

                "adv_tau_hat":
                    "recompute from refreshed advection/TOF authority",

                "log10_Kh":
                    "resample frozen geology along refreshed coordinates",

                "log10_Kz_over_Kh":
                    "resample frozen geology along refreshed coordinates",

                "porosity":
                    "resample frozen paired porosity along refreshed coordinates",

                "pressure_z":
                    "sample refreshed pressure and apply frozen AV3 training normalization only for compatibility diagnostics",

                "target_time_hat":
                    "same AV3 target-time scaling",

                "target_eta_sequence":
                    "recompute from refreshed TOF and target time",

                "nw_hat/no_hat/krw_max_hat/kro_max_hat":
                    "resample frozen AV3 constitutive fields along refreshed coordinates",
            },

            "AV3_checkpoint_status_in_AV4":
                "NOT_AUTHORIZED_FOR_COMMITTED_DYNAMIC_FLOW_TRANSPORT",

            "allowed_use_before_compatibility":
                "diagnostic-only; no committed AV4 transport state",

            "A2_operator_validation_PI_RNN_inference":
                False,

            "compatibility_elevation_requires": [
                "prospectively frozen refreshed-flow teacher/validation protocol",
                "no locked AV3CR0004 Y_true reopening",
                "no post-hoc threshold selection",
                "finite 13-channel reconstruction with no silent clipping",
                "teacher-backed predictive-error evaluation",
                "teacher-backed physics-residual evaluation",
                "explicit PASS decision before committed checkpoint reuse",
            ],

            "failure_or_insufficient_evidence":
                (
                    "AV3 checkpoint remains historical-only and AV4 transport "
                    "training/retraining protocol must be frozen before deployment."
                ),
        }

        gate(
            "A1_checkpoint_reuse_fail_closed",
            channel_checkpoint[
                "AV3_checkpoint_status_in_AV4"
            ]
            == "NOT_AUTHORIZED_FOR_COMMITTED_DYNAMIC_FLOW_TRANSPORT",
        )

        # ------------------------------------------------------------------------------------------
        # Scientific boundaries.
        # ------------------------------------------------------------------------------------------

        boundaries = {
            "A1_execution": {
                "pressure_solve":
                    False,

                "Darcy_flux_recompute":
                    False,

                "Pollock_retrace":
                    False,

                "TOF_recompute":
                    False,

                "EOS_fixed_point":
                    False,

                "PI_RNN_inference":
                    False,

                "training":
                    False,

                "mapback":
                    False,

                "CMG":
                    False,
            },

            "not_claimed": [
                "harmonic mobility is universally optimal",
                "fixed brine-density gravity is a full two-phase gravity closure",
                "AV3 checkpoint is accurate under refreshed-flow channels",
                "a production refresh cadence has been calibrated",
                "dynamic-flow coupling improves plume fidelity",
                "AV4 has executed a refreshed flow epoch",
                "external CMG validates the selected operator",
            ],

            "scope":
                (
                    "A1 freezes a controlled mobility-feedback pressure-refresh operator. "
                    "Dynamic mixture-density gravity and external full-physics validation "
                    "remain outside this milestone."
                ),
        }

        # ------------------------------------------------------------------------------------------
        # Next milestone: one controlled flow-only refresh.
        # ------------------------------------------------------------------------------------------

        handoff = {
            "milestone":
                "POSTV16-AV4-A2",

            "name":
                (
                    "Controlled Validation-Realization Same-Time Spatial-Mobility "
                    "Pressure/Saturation Refresh Execution"
                ),

            "authorized":
                True,

            "execution":
                False,

            "prospective_control_case": {
                "corey_realization":
                    A2_CONTROL_REALIZATION,

                "paired_porosity":
                    A2_CONTROL_POROSITY,

                "partition":
                    A2_CONTROL_PARTITION,

                "canonical_day":
                    A2_CONTROL_DAY,
            },

            "A2_must_execute": [
                "freeze exact parent AV3CR0003 day-365 integrated state before solver execution",
                "construct local-PV cellwise parent component-mass array",
                "execute direct spatial-mobility pressure/saturation fixed point",
                "prove same-time cellwise/global component-mass closure",
                "prove pressure linear residual and Darcy local/global conservation",
                "retrace exact Pollock streamlines and rebuild TOF/SG7D/E37A geometry",
                "prove injector-weight closure and producer capture",
                "write a committed refreshed flow epoch only if every A1 hard gate passes",
            ],

            "PI_RNN_inference":
                False,

            "transport_time_advance":
                False,

            "AV4_dynamic_transport_execution_authorized":
                False,
        }

        decision = {
            "milestone":
                MILESTONE,

            "status":
                STATUS_PASS,

            "protocol_id":
                PROTOCOL_ID,

            "A0_authority_bound":
                True,

            "spatial_mobility_operator_frozen":
                True,

            "harmonic_face_total_mobility_selected":
                True,

            "mobility_scaled_transmissibility_selected":
                True,

            "mobility_scaled_producer_WI_selected":
                True,

            "fixed_reference_brine_gravity_density_selected":
                True,

            "direct_undamped_same_time_Picard_selected":
                True,

            "max_fixed_point_iterations":
                MAX_FIXED_POINT_ITERATIONS,

            "pressure_relative_L2_tolerance":
                PRESSURE_REL_L2_TOL,

            "saturation_Linf_tolerance":
                SATURATION_LINF_TOL,

            "pressure_linear_relative_residual_max":
                PRESSURE_LINEAR_REL_RESIDUAL_MAX,

            "same_time_cellwise_mass_conservation_frozen":
                True,

            "flow_epoch_validation_and_rollback_frozen":
                True,

            "production_periodic_cadence_selected":
                False,

            "production_periodic_cadence_policy":
                "DEFER_UNTIL_SINGLE_REFRESH_OPERATOR_VALIDATION_PASSES",

            "AV3_checkpoint_committed_AV4_reuse_authorized":
                False,

            "pressure_solve_performed":
                False,

            "PI_RNN_inference_performed":
                False,

            "CMG_validation_performed":
                False,

            "AV4_A2_authorized":
                True,

            "AV4_A2_execution_authorized":
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

            "face_mobility_rule":
                FACE_MOBILITY_RULE,

            "reference_mobility_1_per_Pa_s":
                REFERENCE_MOBILITY,

            "gravity_density_policy":
                GRAVITY_DENSITY_POLICY,

            "max_fixed_point_iterations":
                MAX_FIXED_POINT_ITERATIONS,

            "pressure_relative_L2_tolerance":
                PRESSURE_REL_L2_TOL,

            "saturation_Linf_tolerance":
                SATURATION_LINF_TOL,

            "pressure_linear_relative_residual_max":
                PRESSURE_LINEAR_REL_RESIDUAL_MAX,

            "flow_local_relative_L2_max":
                FLOW_LOCAL_REL_L2_MAX,

            "flow_global_relative_mismatch_max":
                FLOW_GLOBAL_REL_MISMATCH_MAX,

            "injector_weight_relative_closure_max":
                INJECTOR_WEIGHT_REL_CLOSURE_MAX,

            "A2_control_realization":
                A2_CONTROL_REALIZATION,

            "A2_control_day":
                A2_CONTROL_DAY,

            "AV3_checkpoint_dynamic_flow_reuse_authorized":
                False,

            "production_periodic_cadence_selected":
                False,

            "scientific_execution":
                False,

            "AV4_A2_authorized":
                True,

            "AV4_A2_execution_authorized":
                False,
        }

        artifacts = {
            "PAD_Stream_POSTV16_AV4_A1_Summary.json":
                json_bytes(summary),

            "POSTV16_AV4_A1_Spatial_Mobility_Pressure_Operator_Contract.json":
                json_bytes(mobility_pressure_contract),

            "POSTV16_AV4_A1_Mass_Conservative_SameTime_Reconciliation_Contract.json":
                json_bytes(reconciliation_contract),

            "POSTV16_AV4_A1_Flow_Epoch_Validation_and_Rollback_Contract.json":
                json_bytes(flow_epoch_contract),

            "POSTV16_AV4_A1_Refresh_State_Machine_and_Cadence_Policy.json":
                json_bytes(state_machine),

            "POSTV16_AV4_A1_13Channel_Reconstruction_and_Checkpoint_Authority_Firewall.json":
                json_bytes(channel_checkpoint),

            "POSTV16_AV4_A1_Scientific_Boundaries.json":
                json_bytes(boundaries),

            "POSTV16_AV4_A1_A2_Handoff_Contract.json":
                json_bytes(handoff),

            "POSTV16_AV4_A1_Decision_Contract.json":
                json_bytes(decision),

            "POSTV16_AV4_A1_Final_Gate_Matrix.csv":
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
            artifacts,
        )

        manifest_rows = []

        for p in sorted(out.iterdir()):

            if (
                p.is_file()
                and p.name
                != "POSTV16_AV4_A1_Artifact_Manifest.csv"
            ):

                manifest_rows.append(
                    {
                        "file":
                            p.name,

                        "sha256":
                            sha256_file(p),

                        "bytes":
                            p.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV4_A1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print("POSTV16-AV4-A1: DYNAMIC-FLOW OPERATOR / FLOW-EPOCH CONTRACT FREEZE PASS")
        print("=" * 214)
        print("Face mobility                            : HARMONIC TOTAL MOBILITY")
        print("Dynamic transmissibility                 : T_ref * lambda_face/lambda_ref")
        print("Dynamic producer WI                      : WI_ref * lambda_cell/lambda_ref")
        print("Gravity density                          : fixed SG3 brine 1020 kg/m3")
        print("Same-time conserved quantity             : cellwise CO2 component mass")
        print("Fixed-point method                       : direct undamped Picard")
        print("Max fixed-point iterations               :", MAX_FIXED_POINT_ITERATIONS)
        print("Pressure relative-L2 tolerance           :", PRESSURE_REL_L2_TOL)
        print("Saturation L-infinity tolerance          :", SATURATION_LINF_TOL)
        print("Pressure linear residual max             :", PRESSURE_LINEAR_REL_RESIDUAL_MAX)
        print("Flow local/global relative gates         : 1e-8 / 1e-8")
        print("Injector weight closure                  : <=1e-10")
        print("Periodic production cadence              : DEFERRED")
        print("AV3 checkpoint committed AV4 reuse       : NOT AUTHORIZED")
        print(
            "A2 controlled case                       : "
            f"{A2_CONTROL_REALIZATION} / {A2_CONTROL_POROSITY} / day {A2_CONTROL_DAY:g}"
        )
        print("Pressure/flow execution in A1            : False")
        print("CMG                                      : Deferred")
        print("POSTV16-AV4-A2                           : AUTHORIZED")
        print("A2 execution                             : NOT YET AUTHORIZED")
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
                repr(exc),

            "gates":
                gates,

            "pressure_solve_performed":
                False,

            "PI_RNN_inference_performed":
                False,

            "CMG_validation_performed":
                False,

            "AV4_A2_authorized":
                False,
        }

        p = blocked / "POSTV16_AV4_A1_Blocked_Report.json"

        if not p.exists():
            p.write_bytes(
                json_bytes(report)
            )

        print()
        print("POSTV16-AV4-A1: BLOCKED")
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
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
