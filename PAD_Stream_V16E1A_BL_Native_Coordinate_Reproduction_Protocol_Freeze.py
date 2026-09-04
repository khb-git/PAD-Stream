#!/usr/bin/env python3
"""
PAD-Stream V16E-1A
Buckley-Leverett Native-Coordinate Reproduction Protocol Freeze

Purpose
-------
Freeze the source-faithful reproduction protocol for the four final
Buckley-Leverett PI-RNN physics phases before any retraining:

  1. Incompressible
  2. Compressible conservative-Godunov
  3. Capillary
  4. Full compressible-capillary conservative-Godunov

This milestone performs NO training and NO TensorFlow import.

Scientific rules
----------------
* The exact final source files are the model-definition authorities.
* Historical saved weights are unavailable.
* Any new weights are NEW V16E reproduction artifacts.
* Native-coordinate teacher reproduction must precede TOF transformation.
* The original source-native 80/20 shuffled profile split is preserved for
  reproduction fidelity, but it is NOT called an independent OOD test.
* No numerical acceptance threshold is invented in V16E-1A.
* Stage-3/Stage-4 stale config metadata is documented explicitly:
    - Stage 3 executable param_dim = 13, while legacy config writer serializes
      the older 12-field TrainConfig tuple.
    - Stage 4 executable param_dim = 14, while legacy config writer serializes
      the older 12-field TrainConfig tuple.
  New V16E manifests must record executable conditioning dimensions correctly.
* EXP-CS1 remains closed and geology0029 remains consumed.
"""

from pathlib import Path
import hashlib
import json
import sys


R = Path(__file__).resolve().parent

OUT = R / "output" / "V16_E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FREEZE"
OUT.mkdir(parents=True, exist_ok=True)

PROTOCOL = OUT / "V16E1A_BL_Native_Coordinate_Reproduction_Protocol.json"
ISSUES = OUT / "V16E1A_Known_Source_Metadata_Issues.json"
ARTIFACTS = OUT / "V16E1A_Reproduction_Artifact_and_Experiment_Contract.json"
HANDOFF = OUT / "V16E1A_Execution_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1A_Summary.json"


# =============================================================================
# V16E-0R authority
# =============================================================================

E0R_SOURCE = R / "PAD_Stream_V16E0R_Corrected_BL_DP_PAD_Stream_Architecture_Provenance_Freeze.py"
E0R_SOURCE_SHA = "aac39e3d74a5b98b2ad13ba2838ca05ec20206f50ddb0ea06c4c26bfe324a405"

E0R_DIR = R / "output" / "V16_E0R_CORRECTED_BL_DP_PAD_STREAM_ARCHITECTURE_FREEZE"
E0R_CORRECTION = E0R_DIR / "V16E0R_Corrected_BL_DP_Model_Lineage_and_Provenance.json"
E0R_ROLES = E0R_DIR / "V16E0R_Corrected_Transport_Integration_Roles.json"
E0R_HANDOFF = E0R_DIR / "V16E0R_Revised_Development_Path.md"
E0R_SUMMARY = E0R_DIR / "PAD_Stream_V16E0R_Summary.json"

E0R_CORRECTION_SHA = "5d64123d29f8ebde016677ad5156181d39868a5e3f56f3853546e66205175c5d"
E0R_ROLES_SHA = "736ea9cc23730d750f295783af8cf76b1ec5cea72c40ea6eba4ade26e8610ab2"
E0R_HANDOFF_SHA = "b11d91ba225f9de328ca786c6b8f5f51c56b2aa38c07a4575b8c9f399bbfd68f"
E0R_SUMMARY_SHA = "0f1df6651d78bb529a214984efae6cc3c657cc85148d4a36a9863bb678693736"

EXPECTED_E0R_STATUS = (
    "V16E_CORRECTED_BL_DP_PAD_STREAM_ARCHITECTURE_AND_PROVENANCE_FROZEN_"
    "FOUR_PHASE_BL_LINEAGE_CONFIRMED_"
    "HYBRID_10_AND_12_PARAM_DP_LINEAGE_CONFIRMED_"
    "EIGHT_LAYER_REFERENCE_NOT_ARCHITECTURE_LIMIT_"
    "LEGACY_WEIGHTS_UNAVAILABLE_NEW_REPRODUCTION_REQUIRED_"
    "V16E1A_PROTOCOL_FREEZE_AUTHORIZED_TRAINING_NOT_YET_AUTHORIZED"
)


# =============================================================================
# Exact BL source authorities
# =============================================================================

BL = {
    "INC": {
        "phase": "incompressible",
        "experiment_id": "V16E-BLREP-INC-001",
        "source": R / "pi_rnn_stage1_incompressible.py",
        "sha256": "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58",
        "teacher": "analytical Buckley-Leverett rarefaction + Welge shock/tangent construction",
        "sequence_coordinate": "xi = xD / xD_star on the pre-breakthrough fan",
        "input_sequence_features": ["xi"],
        "effective_conditioning": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_star", "Sw_star",
        ],
        "effective_param_dim": 10,
        "legacy_condition_on_dim": 10,
        "hidden": 64,
        "layers": 2,
        "seed": 1337,
        "source_train_frac": 0.8,
        "source_epochs": 400,
        "source_batch_size": 8192,
        "loss_weights": {
            "data": 1.0,
            "physics": 0.05,
            "injector_bc": 5.0,
            "tip_bc": 5.0,
            "anchor": 10.0,
            "monotonicity": 0.2,
            "shape": 0.0,
        },
        "native_metrics": ["MSE", "MAE", "max_abs_error"],
        "legacy_weight_basename": "pi_rnn_fan_multicase_corey.weights.h5",
        "legacy_config_basename": "pi_rnn_fan_multicase_corey_config.json",
        "dataset_semantics":
            "source-generated multi-case analytical fan profiles; six times per valid case; "
            "80/20 shuffled profile split using seed 1337",
        "nesting_or_limit_checks": [
            "analytical shock/front consistency",
            "saturation bounds",
            "fan monotonicity where source physics requires it",
        ],
    },

    "COMP": {
        "phase": "compressible",
        "experiment_id": "V16E-BLREP-COMP-001",
        "source": R / "pi_rnn_stage2_compressible_godunov.py",
        "sha256": "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397",
        "teacher": "conservative compressible Godunov Buckley-Leverett solver",
        "sequence_coordinate": "xi fan coordinate with Stage-2 compressible travel-time/front transform",
        "input_sequence_features": ["xi"],
        "effective_conditioning": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_star", "Sw_star", "Nc",
        ],
        "effective_param_dim": 11,
        "legacy_condition_on_dim": 11,
        "hidden": 64,
        "layers": 2,
        "seed": 1337,
        "source_train_frac": 0.8,
        "source_epochs": 400,
        "source_batch_size": 8192,
        "loss_weights": {
            "data": 1.0,
            "physics": 0.05,
            "injector_bc": 5.0,
            "tip_bc": 5.0,
            "anchor": 10.0,
            "monotonicity": 0.2,
            "shape": 0.0,
        },
        "native_metrics": ["MSE", "MAE", "max_abs_error", "front_error"],
        "legacy_weight_basename": "pi_rnn_fan_stage2_godunov.weights.h5",
        "legacy_config_basename": "pi_rnn_fan_stage2_godunov_config.json",
        "dataset_semantics":
            "Godunov targets over Nc grid [0, 0.05, 0.10, 0.20, 0.30]; "
            "0.95 breakthrough horizon; six times; source uses 80/20 shuffled "
            "profile split with seed 1337",
        "nesting_or_limit_checks": [
            "Nc = 0 nests Stage-1 behavior",
            "teacher comparison against conservative Godunov reference",
            "saturation bounds",
        ],
    },

    "CAP": {
        "phase": "capillary",
        "experiment_id": "V16E-BLREP-CAP-001",
        "source": R / "pi_rnn_stage3_capillary.py",
        "sha256": "dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f",
        "teacher":
            "capillary Buckley-Leverett numerical teacher: explicit Godunov/upwind "
            "advection plus implicit capillary diffusion",
        "sequence_coordinate":
            "native xD sequence on the deterministic conditioning grid; N_SEQ = 64 "
            "with dense output by interpolation",
        "input_sequence_features": [
            "xD",
            "relative-front coordinate generated inside model: xD - xD_front",
        ],
        "base_conditioning_12": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_front", "Sw_star", "inv_Pec", "lambda_bc",
        ],
        "derived_conditioning": ["log10(mu_w / mu_o)"],
        "effective_conditioning": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_front", "Sw_star", "inv_Pec", "lambda_bc",
            "log10(mu_w / mu_o)",
        ],
        "effective_param_dim": 13,
        "legacy_condition_on_dim": 12,
        "hidden": 64,
        "layers": 2,
        "seed": 1337,
        "source_train_frac": 0.8,
        "source_epochs": 2000,
        "source_batch_size_runtime": 4096,
        "trainconfig_batch_size_field": 16384,
        "loss_weights": {
            "data": 1.0,
            "physics_PDE": 0.10,
            "injector_bc": 5.0,
            "outlet_bc": 5.0,
            "anchor": 2.0,
            "monotonicity": 5.0,
            "mass": 20.0,
            "curvature": 1e-6,
            "shape": 0.5,
        },
        "native_metrics": [
            "profile MAE",
            "profile max_abs_error",
            "front_error",
            "mass/inventory behavior",
            "source diagnostic sweeps over Pe_c and lambda_bc",
        ],
        "legacy_weight_basename": "pi_rnn_stage3_capillary_v9.weights.h5",
        "legacy_config_basename": "pi_rnn_stage3_capillary_v9_config.json",
        "dataset_semantics":
            "Pe_c grid [10, 22, 50, 100], lambda_bc grid [1.5, 2, 3], "
            "source max_cases 2400, six times, native N_SEQ=64, "
            "80/20 shuffled profile split with seed 1337",
        "nesting_or_limit_checks": [
            "sharp-capillary-limit evaluation is diagnostic/extrapolative, not a trained discontinuous target",
            "fine-grid capillary teacher comparison",
            "saturation bounds",
            "mass/front consistency",
        ],
    },

    "FULL": {
        "phase": "full_compressible_capillary_godunov",
        "experiment_id": "V16E-BLREP-FULL-001",
        "source": R / "pi_rnn_stage4_full_godunov.py",
        "sha256": "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a",
        "teacher":
            "full compressible-capillary conservative-Godunov transport with "
            "u_D(xD)=exp(Nc*xD) and implicit capillary diffusion",
        "sequence_coordinate":
            "native xD sequence on deterministic conditioning grid; N_SEQ = 64",
        "input_sequence_features": [
            "xD",
            "relative-front coordinate generated inside model: xD - xD_front",
        ],
        "base_conditioning_12": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_front", "Sw_star", "inv_Pec", "lambda_bc",
        ],
        "added_conditioning": ["Nc", "log10(mu_w / mu_o)"],
        "effective_conditioning": [
            "no", "nw", "swi", "sor", "mu_w", "mu_o", "phi",
            "tD", "xD_front", "Sw_star", "inv_Pec", "lambda_bc",
            "Nc", "log10(mu_w / mu_o)",
        ],
        "effective_param_dim": 14,
        "legacy_condition_on_dim": 12,
        "hidden": 64,
        "layers": 2,
        "seed": 1337,
        "source_train_frac": 0.8,
        "source_epochs": 1000,
        "source_batch_size_runtime": 4096,
        "trainconfig_batch_size_field": 256,
        "loss_weights": {
            "data": 1.0,
            "physics_PDE": 0.10,
            "injector_bc": 5.0,
            "outlet_bc": 5.0,
            "anchor": 2.0,
            "monotonicity": 5.0,
            "mass": 20.0,
            "curvature": 1e-6,
            "shape": 0.5,
        },
        "native_metrics": [
            "profile MAE",
            "profile max_abs_error",
            "front_error",
            "mass/inventory behavior",
            "Nc accuracy sweep",
            "breakthrough-shift check",
            "Stage-3 nesting check at Nc=0",
        ],
        "legacy_weight_basename": "pi_rnn_stage4_full_godunov.weights.h5",
        "legacy_config_basename": "pi_rnn_stage4_full_godunov_config.json",
        "dataset_semantics":
            "Pe_c grid [10, 22, 50, 100], lambda_bc grid [1.5, 2, 3], "
            "Nc grid [0, 0.05, 0.1, 0.2], source max_cases 2400, six times, "
            "native N_SEQ=64, 80/20 shuffled profile split with seed 1337",
        "nesting_or_limit_checks": [
            "Nc = 0 nests Stage-3 capillary physics",
            "full conservative-Godunov teacher comparison",
            "breakthrough-shift consistency",
            "saturation bounds",
            "mass/front consistency",
        ],
    },
}


# =============================================================================
# Source semantic fingerprints
# =============================================================================

MARKERS = {
    "INC": [
        'condition_on: Tuple[str, ...]',
        '"tD", "xD_star", "Sw_star"',
        'epochs: int = 400',
        'seed: int = 1337',
        'pi_rnn_fan_multicase_corey.weights.h5',
        'train_frac=0.8',
    ],
    "COMP": [
        '"Nc"',
        'param_dim: int = 11',
        'epochs: int = 400',
        'seed: int = 1337',
        'pi_rnn_fan_stage2_godunov.weights.h5',
        'nc_vals = np.array([0.0, 0.05, 0.10, 0.20, 0.30]',
    ],
    "CAP": [
        'PARAM_DIM_V7 = 13',
        'N_SEQ = 64',
        'append_logM',
        'epochs: int = 2000',
        'pi_rnn_stage3_capillary_v9.weights.h5',
        'pec_vals = np.array([10.0, 22.0, 50.0, 100.0]',
    ],
    "FULL": [
        'PARAM_DIM_S4 = 14',
        'N_SEQ = 64',
        'CONSERVATIVE_FORM = True',
        'epochs: int = 1000',
        'pi_rnn_stage4_full_godunov.weights.h5',
        'nc_vals = np.array([0.0, 0.05, 0.1, 0.2]',
    ],
}


# =============================================================================
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def valid_sha(v: str) -> bool:
    return (
        isinstance(v, str)
        and len(v) == 64
        and all(c in "0123456789abcdef" for c in v.lower())
    )


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def contains_all(path: Path, markers):
    if not path.exists():
        return {m: False for m in markers}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m: (m in text) for m in markers}


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-1A")
    print("BL Native-Coordinate Reproduction Protocol Freeze")
    print("=" * 78)

    print(
        "\nPROTOCOL ONLY — no TensorFlow import, no model/checkpoint load, "
        "no NPZ load, no OOD reopening, no training, no inference.\n"
    )

    if any(p.exists() for p in [PROTOCOL, ISSUES, ARTIFACTS, HANDOFF, SUMMARY]):
        raise RuntimeError(
            "V16E-1A outputs already exist. Refusing to overwrite frozen protocol."
        )

    gates = {
        "E0R_source_SHA_valid": valid_sha(E0R_SOURCE_SHA),
        "E0R_correction_SHA_valid": valid_sha(E0R_CORRECTION_SHA),
        "E0R_roles_SHA_valid": valid_sha(E0R_ROLES_SHA),
        "E0R_handoff_SHA_valid": valid_sha(E0R_HANDOFF_SHA),
        "E0R_summary_SHA_valid": valid_sha(E0R_SUMMARY_SHA),

        "E0R_source_SHA_exact": exact_sha(E0R_SOURCE, E0R_SOURCE_SHA),
        "E0R_correction_SHA_exact": exact_sha(E0R_CORRECTION, E0R_CORRECTION_SHA),
        "E0R_roles_SHA_exact": exact_sha(E0R_ROLES, E0R_ROLES_SHA),
        "E0R_handoff_SHA_exact": exact_sha(E0R_HANDOFF, E0R_HANDOFF_SHA),
        "E0R_summary_SHA_exact": exact_sha(E0R_SUMMARY, E0R_SUMMARY_SHA),
    }

    e0r = read_json(E0R_SUMMARY) if E0R_SUMMARY.exists() else {}
    gates.update({
        "E0R_status_exact": e0r.get("status") == EXPECTED_E0R_STATUS,
        "E0R_training_not_authorized":
            e0r.get("training_authorized") is False,
        "E0R_Round_recovery_retired":
            e0r.get("Round_1_2_3_recovery_required") is False,
        "E0R_E0D_obsolete": e0r.get("E0D_obsolete") is True,
    })

    print("E0R AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-1A blocked: E0R authority mismatch.")

    semantic_fingerprints = {}
    for stage, spec in BL.items():
        gates[f"{stage}_source_SHA_valid"] = valid_sha(spec["sha256"])
        gates[f"{stage}_source_SHA_exact"] = exact_sha(spec["source"], spec["sha256"])

        rec = contains_all(spec["source"], MARKERS[stage])
        semantic_fingerprints[stage] = rec
        for i, passed in enumerate(rec.values(), start=1):
            gates[f"{stage}_semantic_marker_{i:02d}"] = bool(passed)

    if not all(gates.values()):
        print("\nSOURCE SEMANTIC GATES")
        for k, v in gates.items():
            print("[PASS]" if v else "[FAIL]", k)
        raise RuntimeError(
            "V16E-1A blocked: one or more BL source identities/semantics changed."
        )

    # -------------------------------------------------------------------------
    # Protocol
    # -------------------------------------------------------------------------

    protocol_models = {}
    for stage, spec in BL.items():
        protocol_models[stage] = {
            k: (rel(v) if isinstance(v, Path) else v)
            for k, v in spec.items()
        }

    protocol = {
        "milestone": "V16E-1A",
        "role":
            "Prospectively freeze source-faithful native-coordinate reproduction "
            "of the four final BL PI-RNN model definitions.",

        "models": protocol_models,
        "source_semantic_fingerprints": semantic_fingerprints,

        "global_reproduction_rules": {
            "training_order": ["INC", "COMP", "CAP", "FULL"],
            "one_phase_at_a_time": True,
            "native_coordinate_first": True,
            "TOF_transformation_in_V16E1": False,

            "source_native_split":
                "Preserve source-defined 80/20 shuffled profile split with seed 1337.",
            "split_interpretation":
                "Reproduction/holdout split only. It is NOT an independently "
                "locked OOD/generalization test and must not be described as one.",

            "teacher_authority":
                "Each phase is evaluated against its own source-defined "
                "analytical/numerical teacher.",

            "metric_policy":
                "Run and archive the source-defined profile/front/mass/nesting "
                "diagnostics. Do not invent a numeric pass threshold in V16E-1A.",

            "acceptance_threshold_status":
                "NOT_PRE_REGISTERED_IN_SOURCE_AND_NOT_INVENTED",

            "minimum_non_numeric_acceptance_gates": [
                "training/reproduction run completes without source modification",
                "checkpoint and reproduction manifest are written and SHA-bound",
                "predictions are finite",
                "saturation remains within source-defined physical range mapping",
                "source-defined teacher diagnostics execute",
                "source-defined nesting/limit checks execute where applicable",
                "no TOF transformation is used in native reproduction",
            ],

            "future_threshold_rule":
                "If a quantitative threshold is later required, freeze it "
                "prospectively before examining the evaluation set used to judge it.",

            "historical_weight_claim_prohibited": True,
            "new_checkpoint_label":
                "NEW V16E NATIVE-COORDINATE REPRODUCTION",
        },

        "firewall": {
            "EXP_CS1_remains_closed": True,
            "geology0029_remains_consumed": True,
            "no_EXP_CS1_retraining": True,
            "no_geology0029_reuse_as_new_test": True,
            "V16D_is_later_comparison_baseline_only": True,
        },
    }

    PROTOCOL.write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Known source metadata issues
    # -------------------------------------------------------------------------

    issues = {
        "milestone": "V16E-1A",
        "policy":
            "Do not silently alter the final research source. Record stale metadata "
            "separately and make the NEW reproduction manifest reflect the actual "
            "executable interface.",

        "Stage3_capillary": {
            "source_sha256": BL["CAP"]["sha256"],
            "legacy_TrainConfig_condition_on_dim": 12,
            "legacy_config_writer_param_dim_source":
                "P.param_dim() from 12-field TrainConfig.condition_on",
            "actual_executable_param_dim": 13,
            "actual_extra_feature": "log10(mu_w / mu_o)",
            "N_SEQ": 64,
            "classification": "KNOWN_STALE_CONFIG_METADATA",
            "reproduction_rule":
                "Do not load the new reproduction from a config that claims param_dim=12. "
                "The V16E manifest must record effective_param_dim=13 and the appended logM feature.",
        },

        "Stage4_full": {
            "source_sha256": BL["FULL"]["sha256"],
            "legacy_TrainConfig_condition_on_dim": 12,
            "legacy_config_writer_param_dim_source":
                "P.param_dim() from 12-field TrainConfig.condition_on",
            "actual_executable_param_dim": 14,
            "actual_extra_features": [
                "Nc at executable conditioning index 12",
                "log10(mu_w / mu_o) at executable conditioning index 13",
            ],
            "N_SEQ": 64,
            "source_nc_training_grid": [0.0, 0.05, 0.1, 0.2],
            "legacy_config_writer_omits_nc_vals": True,
            "classification": "KNOWN_STALE_CONFIG_METADATA",
            "reproduction_rule":
                "The V16E manifest must record effective_param_dim=14, the full "
                "conditioning order, and nc_vals explicitly. Do not rely on the "
                "legacy config writer alone to reconstruct the executable model.",
        },

        "Stage3_Stage4_batch_size_notes": {
            "Stage3_TrainConfig_field": 16384,
            "Stage3_runtime_dataset_batch": 4096,
            "Stage4_TrainConfig_field": 256,
            "Stage4_runtime_dataset_batch": 4096,
            "reproduction_rule":
                "Use the explicit runtime dataset construction in the authoritative "
                "source when reproducing source behavior; archive both values in the manifest.",
        },
    }

    ISSUES.write_text(json.dumps(issues, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # New V16E artifact contract
    # -------------------------------------------------------------------------

    artifacts = {
        "milestone": "V16E-1A",
        "artifact_root":
            "output/V16_E1B_NATIVE_BL_REPRODUCTIONS/<experiment_id>/",

        "experiments": {
            "INC": {
                "experiment_id": "V16E-BLREP-INC-001",
                "runner_milestone": "V16E-1B1",
                "checkpoint":
                    "V16E_BLREP_INC_001.weights.h5",
                "manifest":
                    "V16E_BLREP_INC_001_Manifest.json",
                "metrics":
                    "V16E_BLREP_INC_001_Metrics.json",
            },
            "COMP": {
                "experiment_id": "V16E-BLREP-COMP-001",
                "runner_milestone": "V16E-1B2",
                "checkpoint":
                    "V16E_BLREP_COMP_001.weights.h5",
                "manifest":
                    "V16E_BLREP_COMP_001_Manifest.json",
                "metrics":
                    "V16E_BLREP_COMP_001_Metrics.json",
            },
            "CAP": {
                "experiment_id": "V16E-BLREP-CAP-001",
                "runner_milestone": "V16E-1B3",
                "checkpoint":
                    "V16E_BLREP_CAP_001.weights.h5",
                "manifest":
                    "V16E_BLREP_CAP_001_Manifest.json",
                "metrics":
                    "V16E_BLREP_CAP_001_Metrics.json",
            },
            "FULL": {
                "experiment_id": "V16E-BLREP-FULL-001",
                "runner_milestone": "V16E-1B4",
                "checkpoint":
                    "V16E_BLREP_FULL_001.weights.h5",
                "manifest":
                    "V16E_BLREP_FULL_001_Manifest.json",
                "metrics":
                    "V16E_BLREP_FULL_001_Metrics.json",
            },
        },

        "required_manifest_fields": [
            "experiment_id",
            "source_path",
            "source_sha256",
            "teacher_role",
            "effective_conditioning_order",
            "effective_param_dim",
            "sequence_coordinate",
            "architecture",
            "seed",
            "train_fraction",
            "dataset_generation_semantics",
            "loss_weights",
            "runtime_batch_size",
            "epochs",
            "checkpoint_sha256",
            "metrics_artifact_sha256",
            "historical_checkpoint_recovery_claim=false",
        ],

        "immutability_rule":
            "Once a phase reproduction is certified, its checkpoint/manifest/metrics "
            "SHAs are frozen and become upstream authority for the next phase.",
    }

    ARTIFACTS.write_text(json.dumps(artifacts, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Handoff
    # -------------------------------------------------------------------------

    handoff = """# PAD-Stream V16E-1A — Execution Handoff

## Protocol status

This milestone freezes the native-coordinate reproduction contract for the four
final Buckley-Leverett PI-RNN phases.

No model has been trained in V16E-1A.

## Reproduction order

1. `V16E-1B1` — incompressible
2. `V16E-1B2` — compressible conservative-Godunov
3. `V16E-1B3` — capillary
4. `V16E-1B4` — full compressible-capillary conservative-Godunov

Each phase is certified before the next one begins.

## Why the original coordinates are preserved

The goal of V16E-1B1 through V16E-1B4 is source reproducibility, not PAD-Stream
integration.

The model must first reproduce the teacher it was designed to solve.

Only after the four native-coordinate reproductions are understood do we begin
the BL-to-TOF transformation.

## Holdout semantics

The sources use an 80/20 shuffled profile split with seed 1337.

For V16E reproduction this is preserved because the immediate question is
source-faithful reproduction.

It is not an independently locked OOD test and no claim of OOD geology or
independent generalization may be attached to it.

## Stage-3 and Stage-4 metadata

The final executable conditioning interfaces are:

Stage 3:
`[no, nw, swi, sor, mu_w, mu_o, phi, tD, xD_front, Sw_star,
  inv_Pec, lambda_bc, log10(mu_w/mu_o)]`

Effective dimension: **13**.

Stage 4:
`[no, nw, swi, sor, mu_w, mu_o, phi, tD, xD_front, Sw_star,
  inv_Pec, lambda_bc, Nc, log10(mu_w/mu_o)]`

Effective dimension: **14**.

The old config writers serialize stale metadata from the earlier 12-field
TrainConfig tuple. The final source files are not silently edited. The NEW V16E
reproduction manifests will record the actual executable interfaces.

## Accuracy thresholds

V16E-1A intentionally does not invent a numerical pass threshold.

The source-defined teacher metrics, front diagnostics, mass behavior, saturation
bounds, and nesting checks are archived during reproduction. Any later numerical
threshold must be frozen prospectively before it is used as a decision gate.

## Immediate next milestone

`V16E-1B1 — Final Incompressible BL PI-RNN Native-Coordinate Reproduction`

That milestone may train a NEW V16E reproduction checkpoint from the exact
frozen Stage-1 source. It does not transform to TOF.
"""

    HANDOFF.write_text(handoff, encoding="utf-8")

    gates.update({
        "protocol_written_nonempty":
            PROTOCOL.exists() and PROTOCOL.stat().st_size > 0,
        "issues_written_nonempty":
            ISSUES.exists() and ISSUES.stat().st_size > 0,
        "artifact_contract_written_nonempty":
            ARTIFACTS.exists() and ARTIFACTS.stat().st_size > 0,
        "handoff_written_nonempty":
            HANDOFF.exists() and HANDOFF.stat().st_size > 0,

        "four_BL_phases_protocol_frozen": True,
        "native_coordinate_before_TOF": True,
        "source_native_split_preserved": True,
        "source_native_split_not_called_OOD": True,
        "no_invented_numeric_threshold": True,

        "Stage3_effective_param_dim_13_frozen": True,
        "Stage4_effective_param_dim_14_frozen": True,
        "Stage3_stale_config_metadata_recorded": True,
        "Stage4_stale_config_metadata_recorded": True,
        "Stage4_nc_vals_manifest_requirement_recorded": True,

        "new_reproduction_ids_frozen": True,
        "historical_checkpoint_claim_prohibited": True,

        "EXP_CS1_remains_closed": True,
        "geology0029_remains_consumed": True,

        "no_TensorFlow_import": True,
        "no_model_load": True,
        "no_checkpoint_load": True,
        "no_NPZ_load": True,
        "no_OOD_reopen": True,
        "no_training": True,
        "no_inference": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    status = (
        "V16E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FROZEN_"
        "FOUR_FINAL_BL_PHASES_BOUND_"
        "STAGE3_13D_STAGE4_14D_EXECUTABLE_INTERFACES_RECONCILED_"
        "SOURCE_NATIVE_HOLDOUT_SEMANTICS_FROZEN_NO_OOD_CLAIM_"
        "NEW_V16E_REPRODUCTION_ARTIFACT_CONTRACT_FROZEN_"
        "V16E1B1_INCOMPRESSIBLE_REPRODUCTION_AUTHORIZED"
        if ok else
        "V16E1A_BL_REPRODUCTION_PROTOCOL_FREEZE_BLOCKED"
    )

    summary = {
        "milestone": "V16E-1A",
        "status": status,

        "protocol_sha256": sha256(PROTOCOL),
        "issues_sha256": sha256(ISSUES),
        "artifact_contract_sha256": sha256(ARTIFACTS),
        "handoff_sha256": sha256(HANDOFF),

        "training_executed_in_E1A": False,
        "training_authorized_next": bool(ok),
        "authorized_next_experiment": (
            "V16E-BLREP-INC-001" if ok else None
        ),

        "next_milestone":
            "V16E-1B1 — Final Incompressible BL PI-RNN Native-Coordinate Reproduction",

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nFROZEN REPRODUCTION ORDER")
    for stage in ["INC", "COMP", "CAP", "FULL"]:
        s = BL[stage]
        print(
            f"  {stage:<4} {s['experiment_id']:<24} "
            f"param_dim={s['effective_param_dim']} seed={s['seed']}"
        )

    print("\nKNOWN SOURCE METADATA ISSUES")
    print("  Stage 3: legacy config metadata = 12 fields; executable interface = 13")
    print("  Stage 4: legacy config metadata = 12 fields; executable interface = 14")
    print("  These are documented, not silently edited.")

    print("\nACCEPTANCE POLICY")
    print("  source-defined diagnostics : FROZEN")
    print("  invented numeric threshold : PROHIBITED")
    print("  80/20 source holdout       : REPRODUCTION HOLDOUT, NOT OOD")

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print(
        "  V16E-1B1 — Final Incompressible BL PI-RNN "
        "Native-Coordinate Reproduction"
    )
    print("  NEW V16E training is authorized only after this protocol passes.")

    print("\nProtocol SHA-256 :", sha256(PROTOCOL))
    print("Issues SHA-256   :", sha256(ISSUES))
    print("Artifacts SHA-256:", sha256(ARTIFACTS))
    print("Handoff SHA-256  :", sha256(HANDOFF))
    print("Summary SHA-256  :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
