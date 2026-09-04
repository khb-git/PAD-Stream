#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2R-XPU
B2Q Native-Conservation Interpretation
+ Corrected Stage-2 Prospective Study / Feasibility Protocol Freeze

Purpose
-------
Freeze the scientific interpretation of V16E-1B2Q and define the next
corrected Stage-2 branch without starting training.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

B2Q decisive evidence
----------------------
1. The exact source-native Godunov pre-clip finite-volume update balance is
   satisfied to machine precision across:
       * two frozen Stage-2 diagnostic cases
       * Nc = 0, 0.05, 0.10, 0.20, 0.30

2. There are zero clipping events in all audited runs, so clipping does not
   alter the teacher trajectory in these diagnostic cases.

3. Continuous finite-difference residuals are NOT equivalent to the exact
   discrete FV balance for a shock-capturing solution.

4. Fan-processing ablation shows:
       * interpolation of the raw smeared numerical shock into the moving fan
         produces very large derivative residuals;
       * the source-defined Sw_star floor removes the shock-tail contamination
         and reduces the dense-fan residual by orders of magnitude;
       * forced endpoint replacement has only a very small additional effect;
       * reducing the temporal trajectory to the source's six retained times
         inflates the finite-difference moving-fan residual again.

5. Corrected PI-RNN training will use autograd derivatives of the network
   output with respect to xi, tD, and xD_star. It will NOT finite-difference
   the six retained supervised time snapshots. Therefore the B2O sparse-time
   audit artifact is not the derivative mechanism used by the prospective
   corrected physics loss.

Scientific branch definition
----------------------------
Prospective model ID:
    V16E-BLREP-COMP-XPU-005

Baseline:
    V16E-BLREP-COMP-XPU-004

One scientific change:
    Replace the retained algebraic characteristic physics loss with the
    B2N/B2O-verified conservative moving-fan residual.

Everything else remains bound to COMP-XPU-004 / frozen Stage-2:
    * [xi, eta] sequence features
    * raw physical 11-D p11
    * no Nc scaling
    * exact Godunov teacher dataset
    * all data / BC / anchor / monotonic losses
    * physics weight lambda_phys = 0.05
    * seed 1337
    * 2 x LSTM(64)
    * Adam lr=1e-3, foreach=False
    * 800 epochs
    * logical batch 8192
    * same 80/20 development-diagnostic split
    * no OOD
    * no TOF

Corrected residual
------------------
For N=N(xi,tD,X,...), X=xD_star(tD),

    R_cons =
        N_tD
        + Xdot*N_X
        - (xi*Xdot/X)*N_xi
        + (1/X) d/dxi[exp(Nc*xi*X)*fw(N)]

with primary physical front-speed closure

    Xdot = exp(Nc*X) * sigma_BL

    sigma_BL =
        [fw(Sw_star)-fw(swc)] / [Sw_star-swc].

The residual is evaluated on interior fan nodes only.

Why training is NOT yet authorized
----------------------------------
Unlike the old characteristic residual, the corrected residual requires
network input derivatives. Training through those derivatives requires
create_graph=True and backward through the derivative graph. For the recurrent
sequence model, local N_xi uses the diagonal sequence Jacobian.

This computational path has not yet been benchmarked on the user's Intel Arc
XPU. Therefore B2R authorizes only:

    V16E-1B2S-XPU

A NO-OPTIMIZER / NO-WEIGHT-UPDATE residual-backward feasibility benchmark.

B2S candidate microbatches:
    1, 2, 4, 8, 16

Selection is operational only:
    choose the largest candidate that completes finite forward + corrected
    residual + backward without OOM/device loss and preserves the frozen
    residual algebraic identities.

No scientific acceptance threshold is introduced.

B3 remains blocked.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2R-XPU"

# =============================================================================
# Frozen source / baseline authorities
# =============================================================================

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

# COMP-XPU-004
COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"
COMP004_MANIFEST = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Manifest.json"
COMP004_MANIFEST_SHA = "989d3aaca374b44a9f6f9d0a35b9b0ddf8a86b3665e5b58f9bbb4f97ad08add7"
COMP004_SUMMARY = COMP004_DIR / "PAD_Stream_V16E1B2J_XPU_Summary.json"
COMP004_SUMMARY_SHA = "d4fc1de7a0257be90f2629e7e1469a30f2e7011d5586e32799f9c2f7338658b0"

# B2N derivation
B2N_DIR = (
    R / "output"
    / "V16_E1B2N_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_DERIVATION"
)
B2N_DERIVATION = B2N_DIR / "V16E1B2N_Conservative_Moving_Fan_Residual_Derivation.json"
B2N_DERIVATION_SHA = "85b6757df96cb256ae4f87d5412f276f92ad8d84600e576b2d34e864b4f35b14"

# B2O autograd verification
B2O_DIR = (
    R / "output"
    / "V16_E1B2O_XPU_CONSERVATIVE_RESIDUAL_AUTOGRAD_VERIFICATION"
)
B2O_AUTOGRAD = B2O_DIR / "V16E1B2O_COMP004_Autograd_Residual_Form_Verification.json"
B2O_AUTOGRAD_SHA = "fb347b81ece990860e2caf599e9d276296a833f800b3c881dfec5235f76bb39e"
B2O_DECISION = B2O_DIR / "V16E1B2O_Residual_Implementation_Decision.json"
B2O_DECISION_SHA = "447051f466b1b688b1d0127922921919edbd13c86b7e4d4e99591fa8ba9f2425"

# B2P protocol authority
B2P_DIR = (
    R / "output"
    / "V16_E1B2P_XPU_B2O_INTERPRETATION_NATIVE_TEACHER_PROTOCOL_FREEZE"
)
B2P_PROTOCOL = B2P_DIR / "V16E1B2P_Native_Godunov_Verification_Protocol.json"
B2P_PROTOCOL_SHA = "553288b7e18c012d87c977efd6742bc5719f3e5f05e37734fe5e6f595590ae0d"

# B2Q authority
B2Q_SOURCE = (
    R
    / "PAD_Stream_V16E1B2Q_XPU_Source_Native_Godunov_Conservation_and_Fan_Ablation.py"
)
B2Q_SOURCE_SHA = "4f8fc234d92dec1598da6e56e726b2a0be4e67a97163ab3304d2823f2811f6ea"

B2Q_DIR = (
    R / "output"
    / "V16_E1B2Q_XPU_SOURCE_NATIVE_GODUNOV_CONSERVATION_AUDIT"
)
B2Q_NATIVE = B2Q_DIR / "V16E1B2Q_Native_FV_Discrete_Conservation_Audit.json"
B2Q_ABLATION = B2Q_DIR / "V16E1B2Q_Fan_Processing_Residual_Ablation.json"
B2Q_DECISION = B2Q_DIR / "V16E1B2Q_Native_Teacher_Verification_Decision.json"
B2Q_SUMMARY = B2Q_DIR / "PAD_Stream_V16E1B2Q_XPU_Summary.json"

B2Q_NATIVE_SHA = "e53b6f3707c8b61742625056b8f159998bd31779a608afce0c8490f8d87feb72"
B2Q_ABLATION_SHA = "554e53a65f26604e945110d8ad2f1bf9ae802c715b1ce4ac719147b0d95812f5"
B2Q_DECISION_SHA = "8b0ff97a3e9c68c77642fb33d2e9646d4f36e5d5807b7f87b85b4d7c46b3022c"
B2Q_SUMMARY_SHA = "f6eb8a1cb6581e49f1d851c32b560c853bb768ccb146dcadaa2bd3b6c44d8221"

EXPECTED_B2Q_STATUS = (
    "V16E1B2Q_XPU_SOURCE_NATIVE_GODUNOV_DISCRETE_CONSERVATION_AND_FAN_PROCESSING_ABLATION_COMPLETE_"
    "EXACT_PRECLIP_FINITE_VOLUME_UPDATE_BALANCE_MACHINE_PRECISION_VERIFIED_"
    "POSTCLIP_CORRECTIONS_NATIVE_CONTINUOUS_DIAGNOSTICS_FRONT_EXTRACTION_XI_INTERPOLATION_SWSTAR_FLOOR_"
    "FORCED_ENDPOINT_AND_SPARSE_SIX_TIME_EFFECTS_FROZEN_ACROSS_TWO_SOURCE_CASES_AND_FULL_NC_GRID_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "CORRECTED_STAGE2_TRAINING_PROTOCOL_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2R_XPU_B2Q_INTERPRETATION_CORRECTED_STAGE2_PROTOCOL"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2R_B2Q_Scientific_Interpretation.json"
PROSPECTIVE = OUT / "V16E1B2R_COMP_XPU_005_Prospective_Scientific_Protocol.json"
FEASIBILITY = OUT / "V16E1B2R_B2S_Autograd_Backward_Feasibility_Protocol.json"
HANDOFF = OUT / "V16E1B2R_B2S_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2R_XPU_Summary.json"

PROSPECTIVE_EXPERIMENT = "V16E-BLREP-COMP-XPU-005"
NEXT_MILESTONE = "V16E-1B2S-XPU"


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


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2R-XPU")
    print("B2Q Interpretation + Corrected Stage-2 Prospective / Feasibility Freeze")
    print("=" * 80)
    print("PROTOCOL ONLY — NO TRAINING — NO OPTIMIZER.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2R summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),

        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),

        "COMP004_manifest_SHA_exact":
            exact(COMP004_MANIFEST, COMP004_MANIFEST_SHA),

        "COMP004_summary_SHA_exact":
            exact(COMP004_SUMMARY, COMP004_SUMMARY_SHA),

        "B2N_derivation_SHA_exact":
            exact(B2N_DERIVATION, B2N_DERIVATION_SHA),

        "B2O_autograd_SHA_exact":
            exact(B2O_AUTOGRAD, B2O_AUTOGRAD_SHA),

        "B2O_decision_SHA_exact":
            exact(B2O_DECISION, B2O_DECISION_SHA),

        "B2P_protocol_SHA_exact":
            exact(B2P_PROTOCOL, B2P_PROTOCOL_SHA),

        "B2Q_source_SHA_exact":
            exact(B2Q_SOURCE, B2Q_SOURCE_SHA),

        "B2Q_native_SHA_exact":
            exact(B2Q_NATIVE, B2Q_NATIVE_SHA),

        "B2Q_ablation_SHA_exact":
            exact(B2Q_ABLATION, B2Q_ABLATION_SHA),

        "B2Q_decision_SHA_exact":
            exact(B2Q_DECISION, B2Q_DECISION_SHA),

        "B2Q_summary_SHA_exact":
            exact(B2Q_SUMMARY, B2Q_SUMMARY_SHA),
    }

    b2q_summary = read_json(B2Q_SUMMARY) if B2Q_SUMMARY.exists() else {}
    b2q_native = read_json(B2Q_NATIVE) if B2Q_NATIVE.exists() else {}
    b2q_ablation = read_json(B2Q_ABLATION) if B2Q_ABLATION.exists() else {}
    b2q_decision = read_json(B2Q_DECISION) if B2Q_DECISION.exists() else {}

    gates.update({
        "B2Q_status_exact":
            b2q_summary.get("status") == EXPECTED_B2Q_STATUS,

        "B2Q_new_training_false":
            b2q_summary.get("new_training_authorized") is False,

        "B2Q_B3_false":
            b2q_summary.get("B3_authorized") is False,

        "B2Q_native_discrete_conservation_verified":
            b2q_decision.get("native_discrete_conservation")
            == "MACHINE_PRECISION_VERIFIED_PRECLIP",

        "B2Q_training_false":
            b2q_decision.get("training_authorized") is False,

        "B2Q_decision_B3_false":
            b2q_decision.get("B3_authorized") is False,
    })

    native_cases = b2q_native.get("cases", {})
    ablation_cases = b2q_ablation.get("cases", {})

    expected_cases = {"case1", "case2"}
    expected_nc = {"0.00", "0.05", "0.10", "0.20", "0.30"}

    gates.update({
        "native_two_cases_present":
            set(native_cases.keys()) == expected_cases,

        "ablation_two_cases_present":
            set(ablation_cases.keys()) == expected_cases,

        "native_full_Nc_grid_each_case":
            all(
                set(rec.keys()) == expected_nc
                for rec in native_cases.values()
            ),

        "ablation_full_Nc_grid_each_case":
            all(
                set(rec.keys()) == expected_nc
                for rec in ablation_cases.values()
            ),
    })

    # Freeze direct B2Q observations.
    all_identity_pass = True
    zero_clip_events = True
    floor_reduces_interp_residual = True
    sparse6_exceeds_dense_final = True
    all_observation_metrics_finite = True

    observation_rows = []

    for case_name in sorted(expected_cases):
        for nc in sorted(expected_nc, key=float):
            nrec = native_cases[case_name][nc]
            arec = ablation_cases[case_name][nc]

            identity = nrec["preclip_identity"]
            clip = nrec["clip_correction"]

            interp_mse = float(
                arec[
                    "stage_1_front_extract_plus_interpolate_to_xi"
                ][
                    "interior_1_to_minus1"
                ][
                    "MSE"
                ]
            )

            floor_mse = float(
                arec[
                    "stage_2_plus_Sw_star_floor"
                ][
                    "interior_1_to_minus1"
                ][
                    "MSE"
                ]
            )

            end_mse = float(
                arec[
                    "stage_3_plus_forced_endpoints"
                ][
                    "interior_1_to_minus1"
                ][
                    "MSE"
                ]
            )

            sparse_mse = float(
                arec[
                    "stage_4_exact_source_sparse_six_time_fan"
                ][
                    "interior_1_to_minus1"
                ][
                    "MSE"
                ]
            )

            all_identity_pass &= bool(
                identity[
                    "max_abs_within_machine_bound"
                ]
            )

            zero_clip_events &= (
                int(
                    clip[
                        "clipped_cell_events"
                    ]
                )
                == 0
            )

            floor_reduces_interp_residual &= (
                floor_mse < interp_mse
            )

            sparse6_exceeds_dense_final &= (
                sparse_mse > end_mse
            )

            for value in (
                interp_mse,
                floor_mse,
                end_mse,
                sparse_mse,
            ):
                all_observation_metrics_finite &= finite(value)

            observation_rows.append({
                "case":
                    case_name,
                "Nc":
                    float(nc),
                "FV_preclip_max_abs":
                    float(
                        identity[
                            "max_abs"
                        ]
                    ),
                "clip_events":
                    int(
                        clip[
                            "clipped_cell_events"
                        ]
                    ),
                "fan_interpolation_MSE":
                    interp_mse,
                "plus_Sw_star_floor_MSE":
                    floor_mse,
                "plus_endpoints_MSE":
                    end_mse,
                "sparse6_MSE":
                    sparse_mse,
                "sparse6_over_dense_endpoints":
                    float(
                        sparse_mse
                        / max(
                            end_mse,
                            1e-30,
                        )
                    ),
            })

    gates.update({
        "all_native_FV_identity_gates_pass":
            bool(all_identity_pass),

        "zero_clip_events_all_audited_runs":
            bool(zero_clip_events),

        "Sw_star_floor_reduces_interp_residual_all_runs":
            bool(floor_reduces_interp_residual),

        "sparse6_residual_exceeds_dense_final_all_runs":
            bool(sparse6_exceeds_dense_final),

        "all_observation_metrics_finite":
            bool(all_observation_metrics_finite),
    })

    # B2O implementation must remain certified.
    b2o_auto = read_json(B2O_AUTOGRAD)

    rh = (
        b2o_auto.get("front_speed_closures", {})
        .get("Rankine_Hugoniot", {})
    )

    fd = (
        b2o_auto.get("front_speed_closures", {})
        .get("finite_difference_Godunov_front", {})
    )

    gates.update({
        "B2O_RH_form_identity_pass":
            rh.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            ) is True,

        "B2O_FD_form_identity_pass":
            fd.get(
                "forms_match_within_machine_epsilon_scaled_bound"
            ) is True,

        "B2O_RH_Nc0_nesting_pass":
            rh.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ) is True,

        "B2O_FD_Nc0_nesting_pass":
            fd.get(
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ) is True,
    })

    print("AUTHORITY / INTERPRETATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2R blocked by authority or interpretation evidence gate."
        )

    interpretation = {
        "milestone":
            MILESTONE,

        "classification":
            "B2Q_NATIVE_CONSERVATION_AND_FAN_ABLATION_INTERPRETATION",

        "frozen_observations":
            observation_rows,

        "scientific_findings": {
            "native_teacher_discrete_conservation":
                "VERIFIED_TO_MACHINE_PRECISION",

            "clipping_effect_in_audited_cases":
                "NONE_OBSERVED",

            "continuous_native_residual_role":
                "DIAGNOSTIC_ONLY_NOT_DISCRETE_CONSERVATION_AUTHORITY",

            "fan_interpolation_effect":
                "Raw moving-fan interpolation of the numerically smeared shock "
                "produces large derivative residuals.",

            "Sw_star_floor_effect":
                "The source-defined Sw_star floor reduces the interpolation-only "
                "moving-fan residual in every audited case/Nc combination.",

            "forced_endpoint_effect":
                "Small relative to the preceding interpolation/floor transformation.",

            "six_time_effect":
                "The exact source six-time representation increases the "
                "finite-difference moving-fan residual relative to the dense "
                "postprocessed fan in every audited case/Nc combination.",

            "training_derivative_implication":
                "Prospective corrected PI-RNN physics loss uses network autograd "
                "derivatives, not finite differences across the six supervised times; "
                "therefore the sparse-time derivative artifact is not the derivative "
                "mechanism used by corrected training.",
        },

        "Stage2_residual_readiness":
            "SCIENTIFICALLY_READY_FOR_PROSPECTIVE_CONTROLLED_STUDY",

        "remaining_blocker":
            "XPU computational feasibility of backward through recurrent input "
            "derivatives / second-order autograd graph.",

        "prohibited_conclusions": [
            "the old characteristic residual is restored",
            "processed-fan finite-difference residual becomes the conservation authority",
            "COMP-XPU-004 is overwritten",
            "corrected Stage-2 full training is already authorized",
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

    prospective = {
        "milestone":
            MILESTONE,

        "prospective_experiment_id":
            PROSPECTIVE_EXPERIMENT,

        "baseline":
            "V16E-BLREP-COMP-XPU-004",

        "classification":
            "ONE_FACTOR_CORRECTED_CONSERVATIVE_STAGE2_PI_RNN_STUDY",

        "scientific_hypothesis":
            "Replacing the incompatible algebraic characteristic physics loss with "
            "the B2N/B2O-verified conservative moving-fan residual will align the "
            "physics-informed objective with the exact conservative Godunov teacher "
            "while preserving COMP-XPU-004's best-accuracy architecture.",

        "one_scientific_change": {
            "old_physics_loss":
                "R_char = y(xi*xD_star;Nc) - tD*dfw/dS",

            "new_physics_loss":
                "R_cons = N_tD + Xdot*N_X - (xi*Xdot/X)*N_xi "
                "+ (1/X)*d_xi[exp(Nc*xi*X)*fw(N)]",

            "front_speed":
                "Xdot = exp(Nc*X)*sigma_BL",

            "sigma_BL":
                "[fw(Sw_star)-fw(swc)]/(Sw_star-swc)",

            "residual_nodes":
                "interior fan nodes only",
        },

        "must_remain_identical_to_COMP_XPU_004": {
            "architecture":
                "[xi,eta] sequence features + raw physical 11-D p11",
            "Nc_scaling":
                False,
            "teacher_dataset":
                "exact frozen Stage-2 Godunov fan dataset",
            "epochs":
                800,
            "seed":
                1337,
            "hidden":
                64,
            "layers":
                2,
            "optimizer":
                "Adam",
            "learning_rate":
                1e-3,
            "Adam_foreach":
                False,
            "logical_batch":
                8192,
            "mixed_precision":
                False,
            "loss_weights": {
                "data":
                    1.0,
                "physics":
                    0.05,
                "injector_bc":
                    5.0,
                "tip_bc":
                    5.0,
                "anchor":
                    10.0,
                "monotonicity":
                    0.2,
                "shape":
                    0.0,
            },
            "development_split":
                "same frozen seed-1337 80/20 reproduction-development diagnostic split",
        },

        "evaluation_requirements_after_training": [
            "overall reproduction-development metrics",
            "per-Nc holdout MAE/RMSE/max error",
            "per-Nc corrected conservative physics loss",
            "full-domain and front-excluded Godunov diagnostics",
            "front-position error",
            "model-to-teacher Nc response gain",
            "Nc=0 Stage-1 nesting",
            "saturation bounds",
            "comparison against COMP-XPU-004 and COMP-XPU-002",
        ],

        "training_authorized":
            False,

        "reason_training_not_yet_authorized":
            "Exact corrected residual backward feasibility and operational microbatch "
            "have not yet been established on Intel XPU.",

        "B3_authorized":
            False,
    }

    PROSPECTIVE.write_text(
        json.dumps(
            prospective,
            indent=2,
        ),
        encoding="utf-8",
    )

    feasibility = {
        "milestone":
            MILESTONE,

        "authorized_next_milestone":
            NEXT_MILESTONE,

        "classification":
            "NO_OPTIMIZER_NO_WEIGHT_UPDATE_CORRECTED_RESIDUAL_BACKWARD_FEASIBILITY_BENCHMARK",

        "model":
            "frozen COMP-XPU-004 checkpoint loaded unchanged",

        "dataset":
            "frozen Stage-2 dataset",

        "operation":
            "forward -> corrected conservative residual with create_graph=True -> "
            "total loss backward -> synchronize XPU -> discard gradients; NO optimizer step",

        "candidate_microbatches":
            [1, 2, 4, 8, 16],

        "candidate_order":
            "ascending",

        "operational_selection_rule":
            "Select the largest tested candidate that completes finite forward, "
            "corrected residual construction, backward, and XPU synchronization "
            "without OOM/device loss and while preserving residual-form identity checks.",

        "benchmark_outputs": [
            "success/failure by microbatch",
            "forward+residual+backward wall time",
            "peak XPU memory if runtime API provides it",
            "finite total loss",
            "finite parameter gradients",
            "RH conservative-vs-expanded residual identity",
            "Nc=0 nesting identity",
        ],

        "weight_update":
            False,

        "optimizer":
            False,

        "training":
            False,

        "scientific_settings_changed":
            False,

        "numeric_scientific_threshold":
            None,

        "B3_authorized":
            False,
    }

    FEASIBILITY.write_text(
        json.dumps(
            feasibility,
            indent=2,
        ),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2R-XPU — B2S Feasibility Handoff\n\n"
        "## Scientific status\n\n"
        "The corrected conservative moving-fan residual is now scientifically "
        "ready for a controlled Stage-2 experiment. The native Godunov teacher "
        "is exactly conservative to machine precision in B2Q, and the processed "
        "fan finite-difference artifacts have been separated from the solver balance.\n\n"
        "## Prospective experiment\n\n"
        f"Reserved ID: **{PROSPECTIVE_EXPERIMENT}**\n\n"
        "Only scientific change relative to COMP-XPU-004: replace the old "
        "characteristic physics loss with the corrected conservative moving-fan residual.\n\n"
        "## Do not train yet\n\n"
        "The corrected residual requires differentiating the recurrent network "
        "with respect to xi, tD, and xD_star and then backpropagating through those "
        "derivatives. B2S must benchmark this graph on Intel XPU with NO optimizer "
        "and NO weight update.\n\n"
        "Candidate microbatches: 1, 2, 4, 8, 16.\n\n"
        "After B2S, freeze the operational microbatch and only then authorize the "
        "fresh 800-epoch COMP-XPU-005 training runner.\n\n"
        "B3 remains blocked.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "prospective_protocol_written":
            PROSPECTIVE.exists()
            and PROSPECTIVE.stat().st_size > 0,

        "feasibility_protocol_written":
            FEASIBILITY.exists()
            and FEASIBILITY.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "corrected_residual_scientifically_ready":
            True,

        "one_scientific_change_defined":
            True,

        "COMP004_preserved":
            True,

        "full_training_not_authorized":
            True,

        "B2S_feasibility_authorized":
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
        "V16E1B2R_XPU_B2Q_NATIVE_CONSERVATION_INTERPRETATION_FROZEN_"
        "EXACT_GODUNOV_FINITE_VOLUME_BALANCE_MACHINE_PRECISION_VERIFIED_ZERO_CLIP_EVENTS_"
        "FAN_SHOCK_INTERPOLATION_AND_SPARSE_TIME_CONTINUOUS_RESIDUAL_ARTIFACTS_SEPARATED_"
        "CORRECTED_CONSERVATIVE_MOVING_FAN_RESIDUAL_SCIENTIFICALLY_READY_FOR_PROSPECTIVE_STAGE2_STUDY_"
        "COMP_XPU_005_ONE_FACTOR_PHYSICS_RESIDUAL_REPLACEMENT_DEFINED_BUT_FULL_TRAINING_NOT_YET_AUTHORIZED_"
        "B2S_EXACT_AUTOGRAD_BACKWARD_FEASIBILITY_BENCHMARK_AUTHORIZED_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2R_XPU_PROTOCOL_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "prospective_protocol_sha256":
            sha256(PROSPECTIVE),

        "feasibility_protocol_sha256":
            sha256(FEASIBILITY),

        "handoff_sha256":
            sha256(HANDOFF),

        "prospective_experiment_id":
            PROSPECTIVE_EXPERIMENT,

        "corrected_Stage2_full_training_authorized":
            False,

        "B2S_feasibility_authorized":
            bool(ok),

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2S-XPU — no-optimizer/no-weight-update Intel XPU "
                "benchmark of exact corrected-residual create_graph=True backward "
                "for microbatches 1,2,4,8,16"
                if ok else
                "V16E-1B2R-R1 — diagnose interpretation/protocol gate failure"
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
    print("  Interpretation :", sha256(INTERPRETATION))
    print("  Prospective    :", sha256(PROSPECTIVE))
    print("  Feasibility    :", sha256(FEASIBILITY))
    print("  Handoff        :", sha256(HANDOFF))
    print("  Summary        :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
