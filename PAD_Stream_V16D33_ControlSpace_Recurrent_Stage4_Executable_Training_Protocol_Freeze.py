#!/usr/bin/env python3
"""
PAD-Stream V16D-33
Control-Space Recurrent Stage-4 Model Architecture +
Executable Training / Validation-Selection / Checkpoint Protocol Freeze

This milestone is CONTRACT ONLY.

It freezes all remaining executable ML choices BEFORE any training on the new
36-case control-space learning dataset.

It does NOT:
  * train a model,
  * open any Y array,
  * evaluate VALIDATION numerically,
  * open or evaluate LOCKED_OOD_TEST,
  * tune architecture/loss/batch size/seed/patience,
  * select a checkpoint.

Scientific design
-----------------
Use the same C20/EXP-MC1 predictive recurrent baseline architecture used in the
earlier multi-foundation-case experiment:

    Input (201,9)
      -> LSTM(64, return_sequences=True)
      -> LSTM(64, return_sequences=True)
      -> TimeDistributed Dense(1, sigmoid)
      -> affine rescale to Sw in [0.2,0.8]

This deliberately holds model capacity/objective fixed while expanding the
training problem from fixed-control geology generalization to joint
geology + control-space generalization.

Future training execution is V16D-33-R1.
"""

from pathlib import Path
import hashlib
import json
import sys


# =============================================================================
# ROOT / OUTPUT
# =============================================================================

R = Path(__file__).resolve().parent

O = (
    R
    / "output"
    / "V16_D33_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_PROTOCOL_FREEZE"
)
O.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FROZEN D32 LEARNING-DATASET AUTHORITIES
# =============================================================================

D32 = (
    R
    / "output"
    / "V16_D32_CONTROLSPACE_36CASE_STAGE4_LEARNING_DATASET_TRAIN_ONLY_NORMALIZATION"
)

D32_SUMMARY = D32 / "PAD_Stream_V16D32_Summary.json"
D32_STATS = D32 / "V16D32_TRAIN_Only_Normalization_Statistics.json"
D32_FEATURE_CONTRACT = (
    D32 / "V16D32_ControlSpace_C20_9Channel_Predictor_Contract.json"
)
D32_PREDICTOR_MANIFEST = D32 / "V16D32_36Case_Predictor_Manifest.json"
D32_DATASET_REGISTRY = D32 / "V16D32_Frozen_36Case_Learning_Dataset_Registry.json"

D32_SHA = {
    "summary":
        "ede1f7b506e1ed3256e5392664d9ff38d83850b5e1cbcf4a8d2b4c2295971801",
    "normalization":
        "dcda1cf01fa30bd1cd947a500de73295037d6ca2b492725edd050c0ff7c3bfd9",
    "feature_contract":
        "6f3301a57281ab2b5d44ffe044758c4707a9a489b2ceaff13867b5f55285b23a",
    "predictor_manifest":
        "70171305a74d512903b5ae75386a86d3110d5f90d9aee99640e858660610d8ee",
    "dataset_registry":
        "9429b239626fbfc8fe8569a2214a79a7abd5e40fbc38ac9112ba236e547fb90d",
}


# =============================================================================
# FROZEN ONE-TOUCH OOD CONTRACT AUTHORITY
# =============================================================================

D31D = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)

D31D_CONTRACT = D31D / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D / "PAD_Stream_V16D31D_Summary.json"

D31D_CONTRACT_SHA = (
    "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
)
D31D_SUMMARY_SHA = (
    "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3"
)


# =============================================================================
# FROZEN EXPERIMENT
# =============================================================================

EXPERIMENT = "EXP-CS1"
SEED = 161501

TRAIN_CASES = 18
VALIDATION_CASES = 9
OOD_CASES = 9

TARGET_TIMES = 9
STREAMLINES = 1078
NODES = 201
CHANNELS = 9

TRAIN_SAMPLES = TRAIN_CASES * TARGET_TIMES * STREAMLINES
VALIDATION_SAMPLES = VALIDATION_CASES * TARGET_TIMES * STREAMLINES

FEATURES = [
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


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text())


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-33")
    print(
        "Control-Space Recurrent Stage-4 Executable Training / "
        "Validation-Selection Protocol Freeze"
    )
    print("=" * 78)

    print(
        "\nD33 IS CONTRACT ONLY.\n"
        "NO MODEL IS TRAINED. NO Y ARRAY IS OPENED. "
        "LOCKED OOD REMAINS SEALED.\n"
    )

    # -------------------------------------------------------------------------
    # 1. Exact upstream SHA gates
    # -------------------------------------------------------------------------

    gates = {
        "D32_summary_SHA_exact":
            exact_sha(D32_SUMMARY, D32_SHA["summary"]),

        "D32_normalization_SHA_exact":
            exact_sha(D32_STATS, D32_SHA["normalization"]),

        "D32_feature_contract_SHA_exact":
            exact_sha(
                D32_FEATURE_CONTRACT,
                D32_SHA["feature_contract"],
            ),

        "D32_predictor_manifest_SHA_exact":
            exact_sha(
                D32_PREDICTOR_MANIFEST,
                D32_SHA["predictor_manifest"],
            ),

        "D32_dataset_registry_SHA_exact":
            exact_sha(
                D32_DATASET_REGISTRY,
                D32_SHA["dataset_registry"],
            ),

        "D31D_contract_SHA_exact":
            exact_sha(
                D31D_CONTRACT,
                D31D_CONTRACT_SHA,
            ),

        "D31D_summary_SHA_exact":
            exact_sha(
                D31D_SUMMARY,
                D31D_SUMMARY_SHA,
            ),
    }

    if not all(gates.values()):
        print("\nPRE-GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError(
            "D33 blocked: exact D32/D31D authority SHA mismatch."
        )

    # -------------------------------------------------------------------------
    # 2. Metadata-only consistency checks
    # -------------------------------------------------------------------------

    d32 = read_json(D32_SUMMARY)
    stats = read_json(D32_STATS)
    feature_contract = read_json(D32_FEATURE_CONTRACT)
    registry = read_json(D32_DATASET_REGISTRY)
    d31d = read_json(D31D_SUMMARY)

    gates.update(
        {
            "D32_status_authorizes_training_protocol_freeze": (
                d32.get("status")
                == "V16D_CONTROLSPACE_36CASE_C20_PREDICTOR_DATASET_"
                   "ASSEMBLED_TRAIN_ONLY_NORMALIZATION_FROZEN_OOD_"
                   "REMAINS_SEALED_TRAINING_PROTOCOL_FREEZE_AUTHORIZED"
            ),

            "D32_split_counts_18_9_9": (
                d32.get("split_counts")
                == {
                    "TRAIN": 18,
                    "VALIDATION": 9,
                    "LOCKED_OOD_TEST": 9,
                }
            ),

            "D32_feature_order_exact": (
                d32.get("feature_order") == FEATURES
            ),

            "normalization_fit_TRAIN_ONLY": (
                stats.get("fit_partition") == "TRAIN_ONLY"
            ),

            "validation_transform_only": (
                stats.get("validation_policy") == "TRANSFORM_ONLY"
            ),

            "locked_OOD_transform_only": (
                stats.get("locked_OOD_policy") == "TRANSFORM_ONLY"
            ),

            "target_not_used_for_normalization": (
                stats.get("target_used_for_statistics") is False
            ),

            "feature_contract_9channels_exact": (
                feature_contract.get("feature_order") == FEATURES
            ),

            "predictor_shape_exact": (
                feature_contract.get("shape_per_case")
                == [9, 1078, 201, 9]
            ),

            "registry_generalization_unit_complete_case": (
                registry.get("generalization_unit")
                == "COMPLETE_FOUNDATION_CASE"
            ),

            "registry_split_counts_exact": (
                registry.get("split_counts")
                == {
                    "TRAIN": 18,
                    "VALIDATION": 9,
                    "LOCKED_OOD_TEST": 9,
                }
            ),

            "registry_OOD_geology0029": (
                registry.get("locked_OOD", {}).get("geology")
                == "0029"
            ),

            "registry_OOD_not_opened": (
                registry.get("locked_OOD", {}).get("opened") is False
            ),

            "registry_OOD_not_evaluated": (
                registry.get("locked_OOD", {}).get("evaluated") is False
            ),

            "D31D_OOD_not_opened": (
                d31d.get("OOD_opened") is False
            ),

            "D31D_OOD_not_evaluated": (
                d31d.get("OOD_evaluated") is False
            ),

            "D31D_one_touch_protocol_frozen": (
                d31d.get("one_touch_protocol_frozen") is True
            ),
        }
    )

    # No NPZ loading occurs anywhere in D33.
    gates["no_predictor_npz_opened_in_D33"] = True
    gates["no_target_Y_npz_opened_in_D33"] = True
    gates["no_OOD_array_opened_in_D33"] = True

    # -------------------------------------------------------------------------
    # 3. Freeze executable training protocol
    # -------------------------------------------------------------------------

    protocol = {
        "protocol_id":
            "V16D_EXP_CS1_CONTROLSPACE_EXECUTABLE_TRAINING_PROTOCOL_1.0",

        "milestone": "V16D-33",

        "experiment": EXPERIMENT,

        "purpose":
            "Controlled predictive baseline for joint unseen-geology "
            "generalization across the prospectively frozen 3x3 rate/BHP "
            "control grid.",

        "experimental_design": {
            "comparison_principle":
                "Hold recurrent architecture/objective fixed relative to the "
                "earlier EXP-MC1 baseline; change the physical learning dataset "
                "and control-space coverage, not model capacity.",

            "TRAIN":
                "18 complete Foundation Cases: geologies 0026-0027, "
                "all 3x3 rate/BHP combinations",

            "VALIDATION":
                "9 complete Foundation Cases: geology0028, "
                "all 3x3 rate/BHP combinations",

            "LOCKED_OOD_TEST":
                "9 complete Foundation Cases: geology0029, "
                "all 3x3 rate/BHP combinations; unavailable to training/"
                "selection and opened only by the separately frozen one-touch "
                "evaluation protocol",

            "generalization_unit":
                "COMPLETE_FOUNDATION_CASE",

            "claim_scope":
                "unseen-geology generalization inside the prospectively frozen "
                "350-650 t/day and 1800-2200 psi control grid; "
                "NOT extrapolation beyond control bounds",
        },

        "dataset_authority": {
            "D32_summary_sha256":
                D32_SHA["summary"],
            "normalization_sha256":
                D32_SHA["normalization"],
            "feature_contract_sha256":
                D32_SHA["feature_contract"],
            "predictor_manifest_sha256":
                D32_SHA["predictor_manifest"],
            "dataset_registry_sha256":
                D32_SHA["dataset_registry"],
            "feature_order":
                FEATURES,
            "predictor_shape_per_case":
                [9, 1078, 201, 9],
            "target_shape_per_case":
                [9, 1078, 201],
            "normalization":
                "immutable TRAIN-only D32 transform",
        },

        "seed": SEED,

        "determinism": {
            "PYTHONHASHSEED": SEED,
            "python_random_seed": SEED,
            "numpy_seed": SEED,
            "tensorflow_seed": SEED,
            "request_tensorflow_op_determinism": True,
            "note":
                "Hardware/library nondeterminism must be recorded if exact "
                "bitwise determinism cannot be achieved; it does not authorize "
                "a protocol change.",
        },

        "model": {
            "name":
                "V16D_EXP_CS1",

            "input_shape":
                [201, 9],

            "architecture": [
                {
                    "layer": "LSTM",
                    "name": "lstm_1",
                    "units": 64,
                    "return_sequences": True,
                },
                {
                    "layer": "LSTM",
                    "name": "lstm_2",
                    "units": 64,
                    "return_sequences": True,
                },
                {
                    "layer": "TimeDistributed(Dense)",
                    "name": "td_sigmoid",
                    "units": 1,
                    "activation": "sigmoid",
                },
                {
                    "layer": "Rescaling",
                    "name": "bounded_Sw_0p2_0p8",
                    "scale": 0.6,
                    "offset": 0.2,
                },
            ],

            "output_shape":
                [201, 1],

            "output_physical_bounds":
                {
                    "Sw_min": 0.2,
                    "Sw_max": 0.8,
                },

            "architecture_lineage":
                "C20 / EXP-MC1 two-layer recurrent predictive baseline",

            "new_architecture_search":
                False,
        },

        "objective": {
            "training_loss":
                "MSE",

            "reported_training_metrics":
                ["MAE"],

            "physics_loss":
                "NONE",

            "reason":
                "EXP-CS1 is the controlled predictive baseline. "
                "Physics-informed loss variants, if studied later, require "
                "a new prospective experiment contract and may not be "
                "selected using locked OOD results.",
        },

        "optimizer": {
            "name": "Adam",
            "learning_rate": 1.0e-3,
            "other_parameters":
                "TensorFlow/Keras defaults unless explicitly serialized "
                "by the future training runner",
        },

        "sampling": {
            "sample_unit":
                "one (FoundationCase, target_time, streamline) sequence",

            "sequence_shape":
                [201, 9],

            "target_shape":
                [201, 1],

            "TRAIN_cases":
                TRAIN_CASES,

            "VALIDATION_cases":
                VALIDATION_CASES,

            "LOCKED_OOD_cases":
                OOD_CASES,

            "TRAIN_samples":
                TRAIN_SAMPLES,

            "VALIDATION_samples":
                VALIDATION_SAMPLES,

            "case_weighting":
                "equal per sequence; each case contributes exactly 9x1078 "
                "streamline-time sequences",

            "TRAIN_shuffle":
                "deterministic shuffle using frozen seed",

            "VALIDATION_shuffle":
                False,

            "batch_size":
                64,
        },

        "loading": {
            "strategy":
                "streaming/memory-safe per-case NPZ loading through "
                "deterministic generator/tf.data",

            "do_not_materialize_all_cases_in_RAM":
                True,

            "TRAIN_XY_access":
                "allowed for gradient updates",

            "VALIDATION_XY_access":
                "allowed only for validation objective/checkpoint selection",

            "LOCKED_OOD_XY_access":
                "PROHIBITED during training/selection",

            "OOD_paths_may_exist_in_registry":
                True,

            "OOD_arrays_may_be_opened":
                False,
        },

        "epochs": {
            "max":
                300,

            "early_stopping": {
                "monitor":
                    "val_loss",

                "mode":
                    "min",

                "patience":
                    25,

                "min_delta":
                    0.0,

                "restore_best_weights":
                    False,
            },
        },

        "checkpoint": {
            "monitor":
                "val_loss",

            "mode":
                "min",

            "save_best_only":
                True,

            "save_weights_only":
                True,

            "selection_authority":
                "minimum raw VALIDATION MSE",

            "ties":
                "retain first checkpoint achieving the minimum under "
                "framework callback semantics",

            "validation_only":
                True,
        },

        "postfit": {
            "reload_best_checkpoint":
                True,

            "reloaded_checkpoint_validation_evaluation":
                True,

            "freeze_architecture_JSON":
                True,

            "freeze_checkpoint_SHA256":
                True,

            "freeze_training_history":
                True,

            "freeze_validation_selection_summary":
                True,

            "LOCKED_OOD_after_training":
                "REMAINS SEALED",

            "next_after_successful_training":
                "freeze final one-touch evaluator source/checkpoint binding "
                "before OOD_OPENED.lock may be created",
        },

        "failure_policy": {
            "serialization_failure":
                "repair/recover already-frozen best weights; do not retrain "
                "merely to repair serialization",

            "OOM":
                "repair loading/execution without changing model/objective; "
                "if batch size must change, freeze D33 revision BEFORE retry",

            "interruption":
                "a restart/resume strategy must preserve the exact D33 "
                "experiment identity; do not silently change seed, dataset, "
                "architecture, optimizer, or validation rule",

            "training_nan_or_nonfinite":
                "stop and diagnose; do not inspect OOD and do not relax "
                "scientific/data gates",

            "validation_result_is_poor":
                "report it; do not open OOD and do not modify this experiment "
                "retroactively",
        },

        "prohibited": [
            "OOD-informed tuning",
            "OOD normalization fit",
            "OOD feature selection",
            "OOD architecture selection",
            "OOD loss design",
            "OOD early stopping",
            "OOD checkpoint selection",
            "OOD threshold tuning",
            "architecture changes after D33 freeze",
            "loss changes after D33 freeze",
            "batch-size changes without a prospective protocol revision",
            "seed changes after D33 freeze",
            "case/streamline/time/node exclusion",
            "direct rate/BHP channel insertion in EXP-CS1",
            "M_face predictor insertion",
            "physics loss in EXP-CS1",
            "retraining solely because validation performance is disappointing",
        ],

        "scientific_scope": {
            "baseline_type":
                "predictive recurrent Stage-4 surrogate",

            "Pollock":
                "authoritative kinematics in predictor construction",

            "ADV":
                "auxiliary directional conditioning",

            "M_face":
                "physics sidecar, not predictor",

            "control_space":
                {
                    "rate_tpd": [350, 500, 650],
                    "producer_bhp_psi": [1800, 2000, 2200],
                },

            "foundation_model_claim":
                "NOT AUTHORIZED BY D33",

            "control_extrapolation_claim":
                "NOT AUTHORIZED",
        },

        "OOD_firewall": {
            "D31D_contract_sha256":
                D31D_CONTRACT_SHA,

            "OOD_geology":
                "0029",

            "training_use":
                False,

            "normalization_fit":
                False,

            "model_selection":
                False,

            "checkpoint_selection":
                False,

            "threshold_selection":
                False,

            "OOD_opened_in_D33":
                False,

            "OOD_evaluated_in_D33":
                False,
        },

        "execution_in_D33": {
            "training":
                False,

            "model_inference":
                False,

            "validation_metric_computation":
                False,

            "target_np_load":
                False,

            "OOD_np_load":
                False,

            "checkpoint_selection":
                False,

            "contract_freeze_only":
                True,
        },
    }

    # -------------------------------------------------------------------------
    # 4. Freeze contract
    # -------------------------------------------------------------------------

    protocol_path = (
        O
        / "V16D33_EXP_CS1_ControlSpace_Executable_Training_Protocol_1.0.json"
    )

    protocol_path.write_text(
        json.dumps(protocol, indent=2)
    )

    # -------------------------------------------------------------------------
    # 5. Final gates
    # -------------------------------------------------------------------------

    gates.update(
        {
            "experiment_EXP_CS1_frozen":
                protocol["experiment"] == "EXP-CS1",

            "architecture_frozen_2xLSTM64":
                protocol["model"]["architecture"][0]["units"] == 64
                and protocol["model"]["architecture"][1]["units"] == 64,

            "C20_9channel_input_frozen":
                protocol["model"]["input_shape"] == [201, 9]
                and protocol["dataset_authority"]["feature_order"] == FEATURES,

            "bounded_output_0p2_0p8":
                protocol["model"]["output_physical_bounds"]
                == {"Sw_min": 0.2, "Sw_max": 0.8},

            "MSE_only_no_physics_loss":
                protocol["objective"]["training_loss"] == "MSE"
                and protocol["objective"]["physics_loss"] == "NONE",

            "Adam_1e_3_frozen":
                protocol["optimizer"]["name"] == "Adam"
                and protocol["optimizer"]["learning_rate"] == 1.0e-3,

            "seed_161501_frozen":
                protocol["seed"] == 161501,

            "batch_size_64_frozen":
                protocol["sampling"]["batch_size"] == 64,

            "TRAIN_samples_exact":
                protocol["sampling"]["TRAIN_samples"] == 174636,

            "VALIDATION_samples_exact":
                protocol["sampling"]["VALIDATION_samples"] == 87318,

            "max_epochs_300_frozen":
                protocol["epochs"]["max"] == 300,

            "early_stopping_val_loss_patience25_frozen":
                protocol["epochs"]["early_stopping"]
                == {
                    "monitor": "val_loss",
                    "mode": "min",
                    "patience": 25,
                    "min_delta": 0.0,
                    "restore_best_weights": False,
                },

            "checkpoint_min_validation_MSE_only":
                protocol["checkpoint"]["selection_authority"]
                == "minimum raw VALIDATION MSE",

            "TRAIN_gradient_only":
                protocol["loading"]["TRAIN_XY_access"]
                == "allowed for gradient updates",

            "VALIDATION_selection_only":
                protocol["loading"]["VALIDATION_XY_access"]
                == "allowed only for validation objective/checkpoint selection",

            "LOCKED_OOD_training_access_prohibited":
                protocol["loading"]["LOCKED_OOD_XY_access"]
                == "PROHIBITED during training/selection",

            "no_direct_control_channels":
                "direct rate/BHP channel insertion in EXP-CS1"
                in protocol["prohibited"],

            "M_face_not_predictor":
                "M_face predictor insertion"
                in protocol["prohibited"],

            "no_training_in_D33":
                protocol["execution_in_D33"]["training"] is False,

            "no_inference_in_D33":
                protocol["execution_in_D33"]["model_inference"] is False,

            "no_Y_opened_in_D33":
                protocol["execution_in_D33"]["target_np_load"] is False,

            "no_OOD_opened_in_D33":
                protocol["execution_in_D33"]["OOD_np_load"] is False,

            "no_checkpoint_selected_in_D33":
                protocol["execution_in_D33"]["checkpoint_selection"] is False,

            "contract_only":
                protocol["execution_in_D33"]["contract_freeze_only"] is True,
        }
    )

    ok = bool(all(gates.values()))

    status = (
        "V16D_EXP_CS1_CONTROLSPACE_RECURRENT_STAGE4_EXECUTABLE_TRAINING_"
        "PROTOCOL_FROZEN_OOD_REMAINS_SEALED_FIRST_TRAINING_RUN_AUTHORIZED"
        if ok
        else "V16D_D33_TRAINING_PROTOCOL_BLOCKED"
    )

    next_milestone = (
        "V16D-33-R1 — Execute frozen EXP-CS1 control-space recurrent "
        "Stage-4 training run and validation-only checkpoint selection"
        if ok
        else "Repair D33 protocol/provenance gate before any training."
    )

    summary_path = O / "PAD_Stream_V16D33_Summary.json"

    summary = {
        "milestone": "V16D-33",
        "experiment": EXPERIMENT,
        "status": status,
        "protocol_sha256": sha256(protocol_path),
        "D32_summary_sha256": D32_SHA["summary"],
        "D32_dataset_registry_sha256": D32_SHA["dataset_registry"],
        "D32_normalization_sha256": D32_SHA["normalization"],
        "D31D_contract_sha256": D31D_CONTRACT_SHA,
        "TRAIN_samples": TRAIN_SAMPLES,
        "VALIDATION_samples": VALIDATION_SAMPLES,
        "architecture":
            "LSTM64 -> LSTM64 -> TD Dense sigmoid -> Rescaling[0.2,0.8]",
        "loss": "MSE",
        "optimizer": "Adam(1e-3)",
        "batch_size": 64,
        "seed": SEED,
        "max_epochs": 300,
        "early_stopping_patience": 25,
        "model_trained": False,
        "checkpoint_selected": False,
        "OOD_opened": False,
        "OOD_evaluated": False,
        "gates": gates,
        "next_milestone": next_milestone,
    }

    summary_path.write_text(
        json.dumps(summary, indent=2)
    )

    print("\nFROZEN EXPERIMENT")
    print("  Experiment        :", EXPERIMENT)
    print("  Architecture      : LSTM64 -> LSTM64 -> TD Dense -> Sw[0.2,0.8]")
    print("  Loss              : MSE")
    print("  Optimizer         : Adam, lr=1e-3")
    print("  Seed              :", SEED)
    print("  Batch size        : 64")
    print("  TRAIN samples     :", TRAIN_SAMPLES)
    print("  VALIDATION samples:", VALIDATION_SAMPLES)
    print("  Max epochs        : 300")
    print("  Early stop        : val_loss, patience=25")
    print("  Checkpoint        : minimum raw validation MSE")

    print("\nGATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nLOCKED-OOD STATUS")
    print(
        "  SEALED — no OOD X/Y array opened, no OOD metric computed, "
        "no OOD-informed decision made."
    )

    print("\nNEXT")
    print(" ", next_milestone)

    print("\nProtocol SHA-256:", sha256(protocol_path))
    print("Summary SHA-256 :", sha256(summary_path))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
