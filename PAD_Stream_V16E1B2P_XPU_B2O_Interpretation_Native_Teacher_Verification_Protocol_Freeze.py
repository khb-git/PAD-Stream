#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2P-XPU
B2O Interpretation / Native-Teacher Verification Protocol Freeze

Purpose
-------
Freeze the correct interpretation of V16E-1B2O.

B2O established:
  1. PASS — conservative-form and expanded-form autograd implementations agree
     within a float32-machine-epsilon-derived identity bound.
  2. PASS — the Nc=0 moving-fan nesting identity is exact within the same
     computational bound.
  3. PASS — RH and finite-difference front-speed closures are both executable.
  4. INCONCLUSIVE — the "teacher corrected residual" obtained by finite
     differencing the frozen 64-node fan dataset is NOT a clean validation of
     the continuous conservative PDE.

Why the teacher audit is not closure evidence
---------------------------------------------
The frozen Stage-2 training target is a POSTPROCESSED fan representation, not
the raw Godunov state trajectory:

    raw 1601-cell Godunov snapshot
        -> numerical mid-jump xD_star extraction
        -> interpolation to 64 xi fan nodes
        -> S_fan = maximum(S_fan, Sw_star)
        -> forced injector endpoint
        -> forced fan-tip endpoint
        -> retain only six times from 100 d to 0.95*tBT

Therefore temporal/spatial finite differences of the saved fan targets include
interpolation, clipping/flooring, forced-boundary, sparse-time, and moving-front
extraction effects. They are not equivalent to the source solver's native
finite-volume conservation residual.

Scientific consequence
-----------------------
Do NOT reject the B2N derivation because the processed-fan B2O teacher residual
does not collapse. Conversely, do NOT authorize corrected Stage-2 training yet.

Next required milestone
-----------------------
V16E-1B2Q — source-native Godunov conservation audit.

B2Q must work from the exact Stage-2 solver on its native xD grid and must:
  * preserve the exact Stage-2 source SHA;
  * use the exact conservative finite-volume flux/update;
  * verify the raw discrete conservation balance before fan postprocessing;
  * quantify what each fan-processing operation does to residual behavior;
  * separate native-grid conservation error from interpolation/floor/endpoint
    and sparse-time derivative artifacts;
  * use no training, optimizer, OOD, or TOF.

Only after B2Q may a corrected conservative Stage-2 training protocol be
considered.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2P-XPU"

# ---------------------------------------------------------------------
# Frozen source authority
# ---------------------------------------------------------------------

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

# ---------------------------------------------------------------------
# B2N authority
# ---------------------------------------------------------------------

B2N_SOURCE = (
    R
    / "PAD_Stream_V16E1B2N_XPU_Conservative_Moving_Fan_Residual_Derivation.py"
)
B2N_SOURCE_SHA = "bde47ca9bab21e6156055cf26e50f686f0f417eaeaa42caa7e53d012f79d4bbd"

B2N_DIR = (
    R / "output"
    / "V16_E1B2N_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_DERIVATION"
)
B2N_DERIVATION = B2N_DIR / "V16E1B2N_Conservative_Moving_Fan_Residual_Derivation.json"
B2N_FRONT_AUDIT = B2N_DIR / "V16E1B2N_Godunov_Front_Speed_Closure_Audit.json"
B2N_SUMMARY = B2N_DIR / "PAD_Stream_V16E1B2N_XPU_Summary.json"

B2N_DERIVATION_SHA = "85b6757df96cb256ae4f87d5412f276f92ad8d84600e576b2d34e864b4f35b14"
B2N_FRONT_AUDIT_SHA = "28df3564a306d3e0817490fbfe84ab17dff9b05957b37c5b9afe33f41285f3ea"
B2N_SUMMARY_SHA = "ca8d9030d1250b277361b462cd5c1a79a4d7c8ccc5c0871dfe869374ee29c0f0"

# ---------------------------------------------------------------------
# B2O authority
# ---------------------------------------------------------------------

B2O_SOURCE = (
    R
    / "PAD_Stream_V16E1B2O_XPU_Conservative_Moving_Fan_Residual_Autograd_Verification.py"
)
B2O_SOURCE_SHA = "5d86dbaca969772f8974ef71dfd3cbff0138473589610d13b79572e6ec35d9c5"

B2O_DIR = (
    R / "output"
    / "V16_E1B2O_XPU_CONSERVATIVE_RESIDUAL_AUTOGRAD_VERIFICATION"
)
B2O_AUTOGRAD = B2O_DIR / "V16E1B2O_COMP004_Autograd_Residual_Form_Verification.json"
B2O_TEACHER = B2O_DIR / "V16E1B2O_Godunov_Teacher_Conservative_Residual_Audit.json"
B2O_DECISION = B2O_DIR / "V16E1B2O_Residual_Implementation_Decision.json"
B2O_SUMMARY = B2O_DIR / "PAD_Stream_V16E1B2O_XPU_Summary.json"

B2O_AUTOGRAD_SHA = "fb347b81ece990860e2caf599e9d276296a833f800b3c881dfec5235f76bb39e"
B2O_TEACHER_SHA = "db621f7cb83bb82c38c28974a08f50b21e303d9f615ea5c601e480644b0f608f"
B2O_DECISION_SHA = "447051f466b1b688b1d0127922921919edbd13c86b7e4d4e99591fa8ba9f2425"
B2O_SUMMARY_SHA = "0dbd2b2de6adc42eaffa4a20fc473f4185fa8822f34fa980e846450d3c1a1230"

EXPECTED_B2O_STATUS = (
    "V16E1B2O_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_AUTOGRAD_VERIFICATION_COMPLETE_"
    "COMP_XPU_004_LOCAL_DIAGONAL_JACOBIANS_TD_XDSTAR_CHAIN_RULE_CONSERVATIVE_AND_EXPANDED_FORMS_"
    "MACHINE_PRECISION_CROSSCHECKED_NC0_MOVING_FAN_NESTING_VERIFIED_RH_AND_FD_FRONT_SPEED_CLOSURES_EVALUATED_"
    "GODUNOV_TEACHER_CORRECTED_CONSERVATIVE_RESIDUAL_AUDIT_COMPLETE_NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "CORRECTED_STAGE2_TRAINING_PROTOCOL_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2P_XPU_B2O_INTERPRETATION_NATIVE_TEACHER_PROTOCOL_FREEZE"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2P_B2O_Interpretation.json"
PROTOCOL = OUT / "V16E1B2P_Native_Godunov_Verification_Protocol.json"
HANDOFF = OUT / "V16E1B2P_B2Q_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2P_XPU_Summary.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_contains_all(path: Path, needles):
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2P-XPU")
    print("B2O Interpretation / Native-Teacher Verification Protocol Freeze")
    print("=" * 80)
    print("INTERPRETATION / PROTOCOL ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2P summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),

        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),

        "B2N_source_SHA_exact":
            exact(B2N_SOURCE, B2N_SOURCE_SHA),

        "B2N_derivation_SHA_exact":
            exact(B2N_DERIVATION, B2N_DERIVATION_SHA),

        "B2N_front_audit_SHA_exact":
            exact(B2N_FRONT_AUDIT, B2N_FRONT_AUDIT_SHA),

        "B2N_summary_SHA_exact":
            exact(B2N_SUMMARY, B2N_SUMMARY_SHA),

        "B2O_source_SHA_exact":
            exact(B2O_SOURCE, B2O_SOURCE_SHA),

        "B2O_autograd_SHA_exact":
            exact(B2O_AUTOGRAD, B2O_AUTOGRAD_SHA),

        "B2O_teacher_SHA_exact":
            exact(B2O_TEACHER, B2O_TEACHER_SHA),

        "B2O_decision_SHA_exact":
            exact(B2O_DECISION, B2O_DECISION_SHA),

        "B2O_summary_SHA_exact":
            exact(B2O_SUMMARY, B2O_SUMMARY_SHA),
    }

    b2o = read_json(B2O_SUMMARY) if B2O_SUMMARY.exists() else {}
    autograd = read_json(B2O_AUTOGRAD) if B2O_AUTOGRAD.exists() else {}
    teacher = read_json(B2O_TEACHER) if B2O_TEACHER.exists() else {}

    gates.update({
        "B2O_status_exact":
            b2o.get("status") == EXPECTED_B2O_STATUS,

        "B2O_new_training_false":
            b2o.get("new_training_authorized") is False,

        "B2O_B3_false":
            b2o.get("B3_authorized") is False,
    })

    # Freeze the implementation results exactly as B2O reported them.
    rh = (
        autograd.get("front_speed_closures", {})
        .get("Rankine_Hugoniot", {})
    )
    fd = (
        autograd.get("front_speed_closures", {})
        .get("finite_difference_Godunov_front", {})
    )

    gates.update({
        "RH_form_identity_pass":
            rh.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            ) is True,

        "FD_form_identity_pass":
            fd.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            ) is True,

        "RH_Nc0_nesting_pass":
            rh.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ) is True,

        "FD_Nc0_nesting_pass":
            fd.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ) is True,
    })

    # The exact frozen dataset processing operations that invalidate treating
    # finite differences of saved fan targets as a native-grid PDE residual.
    processing_needles = [
        "S_fan = np.interp(xi * x_star, xD_sol, S_sol)",
        "S_fan = np.maximum(S_fan, Sw_star)",
        "S_fan[0] = 1.0 - p[\"sor\"]",
        "S_fan[-1] = Sw_star",
        "times = np.linspace(",
        "0.95 * t_bt",
        "6,",
        "n_fan=64",
    ]

    gates["fan_postprocessing_source_evidence_exact"] = (
        source_contains_all(
            BASE_RUNNER,
            processing_needles,
        )
    )

    comparison = teacher.get(
        "comparison_to_B2L_old_characteristic_teacher_residual",
        {}
    )

    expected_nc = {"0.00", "0.05", "0.10", "0.20", "0.30"}

    gates.update({
        "teacher_comparison_all_Nc_present":
            set(comparison.keys()) == expected_nc,

        "Nc0_corrected_RH_not_collapsed":
            float(
                comparison["0.00"][
                    "corrected_conservative_RH_teacher_MSE"
                ]
            )
            >
            float(
                comparison["0.00"][
                    "old_characteristic_teacher_MSE"
                ]
            ),

        "Nc0_corrected_FD_not_collapsed":
            float(
                comparison["0.00"][
                    "corrected_conservative_FD_teacher_MSE"
                ]
            )
            >
            float(
                comparison["0.00"][
                    "old_characteristic_teacher_MSE"
                ]
            ),

        "RH_FD_teacher_results_same_order":
            all(
                (
                    max(
                        float(rec["corrected_conservative_RH_teacher_MSE"]),
                        float(rec["corrected_conservative_FD_teacher_MSE"]),
                    )
                    /
                    max(
                        min(
                            float(rec["corrected_conservative_RH_teacher_MSE"]),
                            float(rec["corrected_conservative_FD_teacher_MSE"]),
                        ),
                        1e-30,
                    )
                )
                < 1.2
                for rec in comparison.values()
            ),
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2P blocked by authority or interpretation evidence gate."
        )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2O_VERIFICATION_INTERPRETATION_FREEZE",

        "frozen_results": {
            "autograd_implementation":
                "PASS",

            "conservative_vs_expanded_forms":
                "machine-precision identity cross-check passed for RH and FD Xdot",

            "Nc0_algebraic_nesting":
                "machine-precision identity cross-check passed for RH and FD Xdot",

            "processed_fan_teacher_continuous_residual_validation":
                "INCONCLUSIVE",

            "corrected_training_authorized":
                False,

            "B3_authorized":
                False,
        },

        "why_processed_fan_teacher_audit_is_inconclusive": {
            "raw_teacher_source":
                "conservative finite-volume Godunov solution on NX_TRAIN=1601",

            "saved_training_target":
                "64-node xi fan representation after front extraction, interpolation, "
                "Sw_star flooring, and forced endpoints",

            "time_sampling":
                "six retained times from 100 d to 0.95*tBT",

            "consequence":
                "Finite differences of the saved fan targets mix physical PDE "
                "derivatives with interpolation, clipping/flooring, endpoint overwrite, "
                "front-extraction, moving-domain, and sparse-time effects.",

            "diagnostic_red_flag":
                "At Nc=0 the corrected processed-fan teacher MSE is much larger than "
                "the old characteristic teacher MSE even though the conservative "
                "equation and moving-coordinate derivation must reduce consistently "
                "at the incompressible limit.",

            "RH_vs_FD_observation":
                "RH and FD Xdot produce similar corrected teacher residual magnitudes, "
                "so front-speed closure choice is not the dominant cause of the "
                "processed-fan audit discrepancy.",
        },

        "scientific_interpretation":
            "B2O validates the corrected residual implementation algebra, but does "
            "not yet validate the residual against the underlying numerical teacher. "
            "The saved fan dataset is a supervised-learning representation, not an "
            "appropriate native conservation stencil. A source-native Godunov audit "
            "is required before any corrected Stage-2 optimizer is created.",

        "prohibited_conclusions": [
            "the B2N conservative derivation failed",
            "the corrected residual is validated by the processed-fan audit",
            "RH Xdot should be rejected in favor of FD Xdot based on B2O",
            "COMP-XPU-004 should be modified",
            "corrected Stage-2 training is authorized",
            "B3 is authorized",
        ],
    }

    INTERPRETATION.write_text(
        json.dumps(
            interpretation,
            indent=2,
        ),
        encoding="utf-8",
    )

    protocol = {
        "milestone":
            MILESTONE,

        "next_milestone":
            "V16E-1B2Q-XPU",

        "classification":
            "SOURCE_NATIVE_GODUNOV_CONSERVATION_VERIFICATION_PROTOCOL",

        "goal":
            "Validate the corrected conservative physics against the exact Stage-2 "
            "teacher before fan postprocessing.",

        "authority": {
            "Stage2_source_sha256":
                STAGE2_SHA,
            "base_runner_sha256":
                BASE_RUNNER_SHA,
            "B2N_derivation_sha256":
                B2N_DERIVATION_SHA,
            "B2O_autograd_audit_sha256":
                B2O_AUTOGRAD_SHA,
            "B2O_teacher_audit_sha256":
                B2O_TEACHER_SHA,
        },

        "required_audits": [
            {
                "name":
                    "native_finite_volume_balance",

                "requirement":
                    "Instrument or faithfully reproduce the exact Godunov update on "
                    "the native NX_TRAIN grid and evaluate the discrete conservation "
                    "balance using the same face fluxes and time step.",

                "purpose":
                    "Confirm the numerical teacher is conservative before any fan mapping.",
            },

            {
                "name":
                    "native_grid_continuous_residual_diagnostic",

                "requirement":
                    "Evaluate a continuous-form diagnostic on raw native-grid snapshots "
                    "using sufficiently dense source-native time sampling, while clearly "
                    "separating it from the exact discrete FV balance.",

                "purpose":
                    "Quantify finite-difference/truncation behavior without fan processing.",
            },

            {
                "name":
                    "fan_processing_ablation",

                "requirement":
                    "Apply fan operations sequentially and measure their effect: "
                    "front extraction -> interpolation to xi -> Sw_star flooring -> "
                    "forced endpoints -> sparse six-time sampling.",

                "purpose":
                    "Identify which representation step creates the B2O residual inflation.",
            },

            {
                "name":
                    "Nc0_control",

                "requirement":
                    "Use Nc=0 as the mandatory derivation/audit control case.",

                "purpose":
                    "The corrected conservative formulation must nest the incompressible "
                    "limit before positive-Nc interpretation is accepted.",
            },

            {
                "name":
                    "positive_Nc_sweep",

                "requirement":
                    "Repeat the same audit at physical Nc=0.05, 0.10, 0.20, 0.30.",

                "purpose":
                    "Separate real compressibility effects from representation artifacts.",
            },
        ],

        "front_speed_policy":
            {
                "primary_physical_closure":
                    "Rankine-Hugoniot Xdot = exp(Nc*X)*sigma_BL",

                "diagnostic_alternate":
                    "finite-difference Godunov mid-jump Xdot",

                "reason":
                    "B2N supports RH physically; B2O shows RH-vs-FD is not the dominant "
                    "source of processed-fan residual inflation.",
            },

        "scientific_firewall": {
            "training":
                False,
            "optimizer":
                False,
            "weight_update":
                False,
            "COMP004_modified":
                False,
            "dataset_redefinition":
                False,
            "physical_Nc_changed":
                False,
            "OOD":
                False,
            "TOF":
                False,
            "B3_authorized":
                False,
        },

        "acceptance_policy":
            "No new scientific numeric threshold. Use exact discrete-balance identities, "
            "convergence/truncation behavior, Nc=0 control, and representation-ablation "
            "evidence to decide whether the corrected residual is ready for a training protocol.",
    }

    PROTOCOL.write_text(
        json.dumps(
            protocol,
            indent=2,
        ),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2P-XPU — B2Q Native Godunov Verification Handoff\n\n"
        "## What is certified\n\n"
        "* The B2N conservative moving-fan derivation is preserved.\n"
        "* The B2O autograd implementation cross-check is certified.\n"
        "* Conservative and expanded forms agree to the float32 identity budget.\n"
        "* Nc=0 algebraic nesting is certified.\n\n"
        "## What is NOT certified\n\n"
        "The B2O finite-difference residual of the saved 64-node fan targets is "
        "not accepted as a quantitative validation of the conservative PDE.\n\n"
        "The frozen target is produced by:\n\n"
        "    native 1601-cell Godunov state\n"
        "      -> numerical front extraction\n"
        "      -> interpolation to 64 xi nodes\n"
        "      -> max(S,Sw_star)\n"
        "      -> forced injector/tip endpoints\n"
        "      -> only six retained times\n\n"
        "## B2Q\n\n"
        "Return to the exact source-native Godunov update. First verify the discrete "
        "finite-volume conservation identity using the actual update fluxes. Then "
        "perform a controlled ablation showing how each fan-processing operation "
        "changes the residual diagnostic.\n\n"
        "No optimizer may be created in B2Q. Corrected Stage-2 training and B3 remain blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "protocol_written":
            PROTOCOL.exists()
            and PROTOCOL.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "autograd_implementation_preserved":
            True,

        "processed_fan_teacher_audit_not_promoted_to_validation":
            True,

        "B2Q_native_audit_required":
            True,

        "new_training_not_authorized":
            True,

        "B3_not_authorized":
            True,

        "no_training":
            True,

        "no_optimizer":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2P_XPU_B2O_INTERPRETATION_AND_NATIVE_TEACHER_VERIFICATION_PROTOCOL_FROZEN_"
        "CONSERVATIVE_AUTOGRAD_FORM_IDENTITY_AND_NC0_ALGEBRAIC_NESTING_CERTIFIED_"
        "PROCESSED_64_NODE_SIX_TIME_FAN_TEACHER_CONTINUOUS_RESIDUAL_AUDIT_CLASSIFIED_INCONCLUSIVE_"
        "FAN_INTERPOLATION_FLOOR_ENDPOINT_AND_SPARSE_TIME_EFFECTS_BOUND_AS_POTENTIAL_AUDIT_ARTIFACTS_"
        "SOURCE_NATIVE_GODUNOV_DISCRETE_CONSERVATION_AND_FAN_PROCESSING_ABLATION_REQUIRED_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2P_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "protocol_sha256":
            sha256(PROTOCOL),

        "handoff_sha256":
            sha256(HANDOFF),

        "new_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2Q-XPU — source-native Godunov discrete-conservation "
                "verification plus fan-processing residual ablation; no training"
                if ok else
                "V16E-1B2P-R1 — diagnose interpretation/protocol gate failure"
            ),

        "gates":
            {
                k: bool(v)
                for k, v
                in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Protocol      :", sha256(PROTOCOL))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
