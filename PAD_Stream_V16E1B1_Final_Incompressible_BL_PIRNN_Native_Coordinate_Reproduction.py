#!/usr/bin/env python3
"""
PAD-Stream V16E-1B1
Final Incompressible BL PI-RNN Native-Coordinate Reproduction

Experiment
----------
V16E-BLREP-INC-001

This script performs the first NEW V16E training run authorized by V16E-1A.

It reproduces the exact final incompressible Buckley-Leverett PI-RNN source in
its native pre-breakthrough fan coordinate. It does NOT transform to TOF.

Authority / provenance
----------------------
Source model definition:
  pi_rnn_stage1_incompressible.py
  SHA-256:
  98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58

The historical weights are unavailable. The checkpoint produced here is a NEW
V16E reproduction and must never be described as a recovered historical
checkpoint.

Reproduction fidelity
---------------------
The authoritative source functions are imported and used directly for:
  * parameter grid generation,
  * analytical BL fan teacher generation,
  * source-native 80/20 profile split,
  * 10-dimensional conditioning,
  * model construction,
  * physics/data/BC/anchor/monotonicity losses,
  * training loop,
  * analytical comparison diagnostics.

No source code is modified.

This is NOT an OOD experiment.
EXP-CS1 remains closed.
geology0029 remains consumed.
"""

from __future__ import annotations

import os
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys
import time

import numpy as np


R = Path(__file__).resolve().parent

EXPERIMENT_ID = "V16E-BLREP-INC-001"
OUT = (
    R / "output"
    / "V16_E1B_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

CHECKPOINT = OUT / "V16E_BLREP_INC_001.weights.h5"
CONFIG = OUT / "V16E_BLREP_INC_001_Config.json"
MANIFEST = OUT / "V16E_BLREP_INC_001_Manifest.json"
METRICS = OUT / "V16E_BLREP_INC_001_Metrics.json"
HISTORY = OUT / "V16E_BLREP_INC_001_Training_History.json"
SUMMARY = OUT / "PAD_Stream_V16E1B1_Summary.json"

CONVERGENCE_PNG = OUT / "V16E_BLREP_INC_001_Training_Convergence.png"
DIAG1_PNG = OUT / "V16E_BLREP_INC_001_Diagnostic_Case1.png"
DIAG2_PNG = OUT / "V16E_BLREP_INC_001_Diagnostic_Case2.png"


# =============================================================================
# V16E-1A authority
# =============================================================================

E1A_SOURCE = R / "PAD_Stream_V16E1A_BL_Native_Coordinate_Reproduction_Protocol_Freeze.py"
E1A_SOURCE_SHA = "136306c90e22feda82f4bd2ae32ba0417e3753668331ddc395402e0cdd92623d"

E1A_DIR = R / "output" / "V16_E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FREEZE"
E1A_PROTOCOL = E1A_DIR / "V16E1A_BL_Native_Coordinate_Reproduction_Protocol.json"
E1A_ISSUES = E1A_DIR / "V16E1A_Known_Source_Metadata_Issues.json"
E1A_ARTIFACTS = E1A_DIR / "V16E1A_Reproduction_Artifact_and_Experiment_Contract.json"
E1A_HANDOFF = E1A_DIR / "V16E1A_Execution_Handoff.md"
E1A_SUMMARY = E1A_DIR / "PAD_Stream_V16E1A_Summary.json"

E1A_PROTOCOL_SHA = "207045957d9a88589abd41b30f963adc061a48ad51e4f55402721bd0e99bdfab"
E1A_ISSUES_SHA = "45513abf482aba34ca113ffd84192f8c32b46b2a3ed0da863c524fce7944f54c"
E1A_ARTIFACTS_SHA = "cffd11401b477be3e69fe1f733bf3f9eabd86a369207af42f06b2b0b5a6efa43"
E1A_HANDOFF_SHA = "65dc4fa429daa02b5c22d6e10ac34cb168a6143d662ba39eaffcac6cc67c6c65"
E1A_SUMMARY_SHA = "e2c682f98c2f27316043695fcb71084e9c3130ba6fd77a44e9891fb70ecd059a"

EXPECTED_E1A_STATUS = (
    "V16E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FROZEN_"
    "FOUR_FINAL_BL_PHASES_BOUND_"
    "STAGE3_13D_STAGE4_14D_EXECUTABLE_INTERFACES_RECONCILED_"
    "SOURCE_NATIVE_HOLDOUT_SEMANTICS_FROZEN_NO_OOD_CLAIM_"
    "NEW_V16E_REPRODUCTION_ARTIFACT_CONTRACT_FROZEN_"
    "V16E1B1_INCOMPRESSIBLE_REPRODUCTION_AUTHORIZED"
)


# =============================================================================
# Exact Stage-1 source
# =============================================================================

SOURCE = R / "pi_rnn_stage1_incompressible.py"
SOURCE_SHA = "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58"

SOURCE_MARKERS = [
    "class TrainConfig:",
    "lambda_data: float = 1.0",
    "lambda_phys: float = 0.05",
    "lambda_bc: float = 5.0",
    "lambda_tip: float = 5.0",
    "lambda_anchor: float = 10.0",
    "lambda_mono: float = 0.2",
    "lr: float = 1e-3",
    "epochs: int = 400",
    "hidden: int = 64",
    "layers: int = 2",
    "seed: int = 1337",
    '"tD", "xD_star", "Sw_star"',
    "def train_pi_rnn_from_dataset_with_history",
    'model.save_weights("pi_rnn_fan_multicase_corey.weights.h5")',
]


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


def jsonable(v):
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.floating, np.integer, np.bool_)):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def finite_number(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def import_source_module():
    spec = importlib.util.spec_from_file_location(
        "v16e_stage1_authoritative_source", SOURCE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not build import spec for Stage-1 source.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def batch_holdout_metrics(model, x, p, truth, indices, batch=2048):
    total_sq = 0.0
    total_abs = 0.0
    total_n = 0
    max_abs = 0.0
    finite = True
    lower_violations = 0
    upper_violations = 0

    for start in range(0, len(indices), batch):
        idx = indices[start:start + batch]
        pred = model(
            [x[idx], p[idx]],
            training=False,
        ).numpy()

        y = truth[idx]
        err = pred - y

        finite = finite and bool(np.isfinite(pred).all()) and bool(np.isfinite(err).all())

        abs_err = np.abs(err)
        total_sq += float(np.sum(err * err))
        total_abs += float(np.sum(abs_err))
        total_n += int(err.size)
        max_abs = max(max_abs, float(np.max(abs_err)))

        # Range-map authority: p[:,2] is swc/swi, p[:,3] is sor.
        swc = p[idx, 2].reshape(-1, 1, 1)
        sor = p[idx, 3].reshape(-1, 1, 1)
        lo = swc - 1e-7
        hi = (1.0 - sor) + 1e-7

        lower_violations += int(np.sum(pred < lo))
        upper_violations += int(np.sum(pred > hi))

    mse = total_sq / max(total_n, 1)
    mae = total_abs / max(total_n, 1)

    return {
        "mse": mse,
        "rmse": math.sqrt(mse),
        "mae": mae,
        "max_abs_error": max_abs,
        "n_scalar_predictions": total_n,
        "finite_predictions": finite,
        "lower_bound_violations": lower_violations,
        "upper_bound_violations": upper_violations,
        "bounds_pass":
            lower_violations == 0 and upper_violations == 0,
    }


def dataframe_records(df):
    if df is None:
        return None
    return [
        {str(k): jsonable(v) for k, v in row.items()}
        for row in df.to_dict(orient="records")
    ]


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-1B1")
    print("Final Incompressible BL PI-RNN Native-Coordinate Reproduction")
    print("=" * 78)
    print(f"Experiment: {EXPERIMENT_ID}")
    print(
        "\nNEW V16E TRAINING — source-faithful native-coordinate reproduction. "
        "No TOF transformation. No OOD claim. EXP-CS1 remains closed.\n"
    )

    # Refuse overwriting any already completed experiment.
    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B1 summary already exists. Refusing to rerun/overwrite "
            "the certified experiment identity."
        )

    # -------------------------------------------------------------------------
    # Authority gates before TensorFlow/source import.
    # -------------------------------------------------------------------------

    gates = {
        "E1A_source_SHA_valid": valid_sha(E1A_SOURCE_SHA),
        "E1A_protocol_SHA_valid": valid_sha(E1A_PROTOCOL_SHA),
        "E1A_issues_SHA_valid": valid_sha(E1A_ISSUES_SHA),
        "E1A_artifacts_SHA_valid": valid_sha(E1A_ARTIFACTS_SHA),
        "E1A_handoff_SHA_valid": valid_sha(E1A_HANDOFF_SHA),
        "E1A_summary_SHA_valid": valid_sha(E1A_SUMMARY_SHA),

        "E1A_source_SHA_exact": exact_sha(E1A_SOURCE, E1A_SOURCE_SHA),
        "E1A_protocol_SHA_exact": exact_sha(E1A_PROTOCOL, E1A_PROTOCOL_SHA),
        "E1A_issues_SHA_exact": exact_sha(E1A_ISSUES, E1A_ISSUES_SHA),
        "E1A_artifacts_SHA_exact": exact_sha(E1A_ARTIFACTS, E1A_ARTIFACTS_SHA),
        "E1A_handoff_SHA_exact": exact_sha(E1A_HANDOFF, E1A_HANDOFF_SHA),
        "E1A_summary_SHA_exact": exact_sha(E1A_SUMMARY, E1A_SUMMARY_SHA),

        "Stage1_source_SHA_valid": valid_sha(SOURCE_SHA),
        "Stage1_source_SHA_exact": exact_sha(SOURCE, SOURCE_SHA),
    }

    e1a = read_json(E1A_SUMMARY) if E1A_SUMMARY.exists() else {}
    gates.update({
        "E1A_status_exact": e1a.get("status") == EXPECTED_E1A_STATUS,
        "E1A_authorized_experiment_exact":
            e1a.get("authorized_next_experiment") == EXPERIMENT_ID,
        "E1A_training_authorized_next":
            e1a.get("training_authorized_next") is True,
    })

    source_text = SOURCE.read_text(encoding="utf-8", errors="replace") if SOURCE.exists() else ""
    for i, marker in enumerate(SOURCE_MARKERS, start=1):
        gates[f"Stage1_semantic_marker_{i:02d}"] = marker in source_text

    print("PRE-TRAIN AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B1 blocked before training: authority/source mismatch."
        )

    # Clean partial files from a prior non-certified crash only if SUMMARY does not
    # exist. This does not erase a certified run because certified runs have SUMMARY.
    for p in [
        CHECKPOINT, CONFIG, MANIFEST, METRICS, HISTORY,
        CONVERGENCE_PNG, DIAG1_PNG, DIAG2_PNG,
    ]:
        if p.exists():
            p.unlink()

    # -------------------------------------------------------------------------
    # Import exact source model. Its __main__ does not execute on import.
    # -------------------------------------------------------------------------

    print("\nIMPORTING EXACT STAGE-1 SOURCE")
    S = import_source_module()

    import tensorflow as tf

    print("TensorFlow version:", tf.__version__)
    print("GPUs available:", tf.config.list_physical_devices("GPU"))

    # -------------------------------------------------------------------------
    # Source-faithful configuration and deterministic seeds.
    # -------------------------------------------------------------------------

    P = S.ProjectParams()
    P.validate()
    base_p = P.as_ml_dict()

    if P.param_dim() != 10:
        raise RuntimeError(f"Unexpected Stage-1 param_dim={P.param_dim()}, expected 10.")
    if P.train.seed != 1337:
        raise RuntimeError(f"Unexpected Stage-1 seed={P.train.seed}, expected 1337.")

    tf.keras.utils.set_random_seed(P.train.seed)

    print("\nSOURCE CONFIGURATION")
    print("  param_dim :", P.param_dim())
    print("  hidden    :", P.train.hidden)
    print("  layers    :", P.train.layers)
    print("  epochs    :", P.train.epochs)
    print("  seed      :", P.train.seed)
    print("  condition :", list(P.train.condition_on))

    # -------------------------------------------------------------------------
    # Source teacher dataset.
    # -------------------------------------------------------------------------

    print("\nGENERATING SOURCE-NATIVE PARAMETER GRID")
    param_list = S.generate_param_grid(base_p)
    print("Parameter cases:", len(param_list))

    print("\nBUILDING SOURCE-NATIVE ANALYTICAL FAN ARRAYS")
    xi_all, Sw_all, p10_all, tD_all, anchor_idxs_all, anchor_targs_all = \
        S.build_multi_case_fan_arrays(
            param_list,
            num_times=6,
            t_min_days=100.0,
        )

    n_profiles = int(xi_all.shape[0])
    if n_profiles <= 1:
        raise RuntimeError("Insufficient generated profiles for reproduction.")

    # Exact source split.
    rng = np.random.default_rng(P.train.seed)
    all_idx = np.arange(n_profiles)
    rng.shuffle(all_idx)
    n_train = int(0.8 * n_profiles)
    train_idx = all_idx[:n_train]
    holdout_idx = all_idx[n_train:]

    print("Generated arrays:")
    print("  xi     :", xi_all.shape)
    print("  Sw     :", Sw_all.shape)
    print("  p10    :", p10_all.shape)
    print("  train  :", len(train_idx))
    print("  holdout:", len(holdout_idx))

    # Use the source function to construct the training dataset exactly as written.
    train_ds, _source_holdout_ds = S.make_tf_datasets_from_arrays(
        xi_all, Sw_all, p10_all, tD_all,
        anchor_idxs_all, anchor_targs_all,
        train_frac=0.8,
        batch_size=8192,
        shuffle_buffer=P.train.shuffle_buffer,
        seed=P.train.seed,
    )

    # -------------------------------------------------------------------------
    # Exact source model and training loop.
    # -------------------------------------------------------------------------

    print("\nBUILDING EXACT SOURCE MODEL")
    model = S.build_model(
        input_features=1,
        param_dim=P.param_dim(),
        hidden=P.train.hidden,
        layers=P.train.layers,
    )

    params_fixed = {
        "mu_w": P.rock.mu_w,
        "mu_o": P.rock.mu_o,
        "krw_max": P.rock.krw_max,
        "kro_max": P.rock.kro_max,
    }

    print("\nTRAINING NEW V16E REPRODUCTION")
    t0 = time.time()

    history = S.train_pi_rnn_from_dataset_with_history(
        model,
        params_fixed,
        train_ds,
        epochs=P.train.epochs,
        lambdas=(
            P.train.lambda_data,
            P.train.lambda_phys,
            P.train.lambda_bc,
            P.train.lambda_shape,
        ),
        lambda_anchor=P.train.lambda_anchor,
        lambda_tip=P.train.lambda_tip,
        lambda_mono=P.train.lambda_mono,
        lr=P.train.lr,
        log_every=50,
    )

    training_seconds = float(time.time() - t0)

    print("\nTRAINING COMPLETE")
    print("  epochs :", len(history.get("epoch", [])))
    print("  elapsed:", f"{training_seconds:.3f} s")

    # -------------------------------------------------------------------------
    # Save NEW reproduction checkpoint.
    # -------------------------------------------------------------------------

    model.save_weights(CHECKPOINT)
    if not CHECKPOINT.exists() or CHECKPOINT.stat().st_size <= 0:
        raise RuntimeError("Checkpoint was not written.")

    HISTORY.write_text(
        json.dumps(jsonable(history), indent=2),
        encoding="utf-8",
    )

    # Source-compatible new config; unlike old artifact name, clearly labeled V16E.
    config = {
        "experiment_id": EXPERIMENT_ID,
        "artifact_class": "NEW_V16E_NATIVE_COORDINATE_REPRODUCTION",
        "historical_checkpoint_recovery": False,

        "source_sha256": SOURCE_SHA,
        "phase": "incompressible",
        "teacher":
            "analytical Buckley-Leverett rarefaction + Welge shock/tangent",

        "sequence_coordinate": "xi = xD / xD_star",
        "input_features": 1,
        "param_dim": 10,
        "condition_on": list(P.train.condition_on),

        "hidden": P.train.hidden,
        "layers": P.train.layers,
        "seed": P.train.seed,
        "epochs": P.train.epochs,
        "learning_rate": P.train.lr,
        "runtime_batch_size": 8192,
        "train_fraction": 0.8,

        "loss_weights": {
            "data": P.train.lambda_data,
            "physics": P.train.lambda_phys,
            "injector_bc": P.train.lambda_bc,
            "tip_bc": P.train.lambda_tip,
            "anchor": P.train.lambda_anchor,
            "monotonicity": P.train.lambda_mono,
            "shape": P.train.lambda_shape,
        },

        "parameter_ranges_from_source": {
            "no": [2.0, 4.0, 1.0],
            "nw": [2.0, 4.0, 1.0],
            "sor": [0.10, 0.40, 0.10],
            "swc": [0.10, 0.30, 0.10],
            "mu_o": [0.3, 1.0, 0.1],
            "mu_w": [0.5, 50.0, 5.5],
            "phi": [0.10, 0.30, 0.10],
            "num_times": 6,
            "t_min_days": 100.0,
        },
    }
    CONFIG.write_text(json.dumps(jsonable(config), indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Reproduction-holdout metrics.
    # -------------------------------------------------------------------------

    print("\nEVALUATING SOURCE-NATIVE REPRODUCTION HOLDOUT")
    holdout = batch_holdout_metrics(
        model,
        xi_all,
        p10_all,
        Sw_all,
        holdout_idx,
        batch=2048,
    )

    # Source-defined case diagnostics.
    p_case_1 = S.make_case_from_values(
        base_p,
        no=2.0, nw=2.0,
        swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7,
        phi=0.20,
    )
    p_case_2 = S.make_case_from_values(
        base_p,
        no=3.0, nw=2.0,
        swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9,
        phi=0.25,
    )

    def case_metrics(p_case):
        t_bt = S.breakthrough_time_days(p_case)
        times = np.linspace(100.0, t_bt, 15).tolist()
        df = S.evaluate_times_fan_case(
            model,
            p_case,
            times,
            S.build_fan_profiles,
        )
        return float(t_bt), times, dataframe_records(df)

    case1_bt, case1_times, case1_rows = case_metrics(p_case_1)
    case2_bt, case2_times, case2_rows = case_metrics(p_case_2)

    # Save source convergence figure.
    try:
        lambdas_dict = {
            "data": P.train.lambda_data,
            "physics": P.train.lambda_phys,
            "bc_inj": P.train.lambda_bc,
            "bc_tip": P.train.lambda_tip,
            "anchor": P.train.lambda_anchor,
            "mono": P.train.lambda_mono,
        }
        S.plot_training_convergence(
            history,
            lambdas_dict,
            save_path=str(CONVERGENCE_PNG),
        )
    except Exception as exc:
        print("WARNING: convergence plot failed:", repr(exc))

    # Source diagnostic panels. Agg backend prevents GUI blocking.
    diag1_stats = None
    diag2_stats = None

    try:
        _, diag1_stats = S.plot_diagnostic_panels(
            model,
            p_case_1,
            case1_times,
            case_name="V16E-BLREP-INC-001 Case 1",
            save_path=str(DIAG1_PNG),
        )
    except Exception as exc:
        print("WARNING: Case-1 diagnostic plot failed:", repr(exc))

    try:
        _, diag2_stats = S.plot_diagnostic_panels(
            model,
            p_case_2,
            case2_times,
            case_name="V16E-BLREP-INC-001 Case 2",
            save_path=str(DIAG2_PNG),
        )
    except Exception as exc:
        print("WARNING: Case-2 diagnostic plot failed:", repr(exc))

    metrics = {
        "experiment_id": EXPERIMENT_ID,
        "evaluation_semantics":
            "Source-native reproduction holdout and source-defined analytical "
            "case diagnostics. NOT an OOD test.",

        "dataset": {
            "parameter_case_count": len(param_list),
            "profile_count": n_profiles,
            "train_profile_count": len(train_idx),
            "holdout_profile_count": len(holdout_idx),
            "sequence_shape": list(xi_all.shape[1:]),
            "conditioning_dim": int(p10_all.shape[1]),
        },

        "holdout": holdout,

        "case_1_symmetric": {
            "breakthrough_time_days": case1_bt,
            "rows": case1_rows,
            "diagnostic_stats": jsonable(diag1_stats),
        },

        "case_2_asymmetric": {
            "breakthrough_time_days": case2_bt,
            "rows": case2_rows,
            "diagnostic_stats": jsonable(diag2_stats),
        },

        "training": {
            "epochs_completed": len(history.get("epoch", [])),
            "training_seconds": training_seconds,
            "final_losses": {
                k: (
                    float(v[-1])
                    if isinstance(v, list) and len(v) > 0 and k != "epoch"
                    else (
                        int(v[-1])
                        if k == "epoch" and isinstance(v, list) and len(v) > 0
                        else None
                    )
                )
                for k, v in history.items()
            },
        },

        "threshold_policy":
            "No numerical acceptance threshold was invented or applied.",
    }

    METRICS.write_text(
        json.dumps(jsonable(metrics), indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Post-training scientific gates.
    # -------------------------------------------------------------------------

    case1_finite = (
        case1_rows is not None
        and len(case1_rows) > 0
        and all(
            finite_number(row.get("mse"))
            and finite_number(row.get("mae"))
            and finite_number(row.get("max_abs_err"))
            for row in case1_rows
        )
    )

    case2_finite = (
        case2_rows is not None
        and len(case2_rows) > 0
        and all(
            finite_number(row.get("mse"))
            and finite_number(row.get("mae"))
            and finite_number(row.get("max_abs_err"))
            for row in case2_rows
        )
    )

    gates.update({
        "TensorFlow_imported_only_after_pretrain_authority_gates": True,
        "training_executed": True,
        "training_epoch_count_exact":
            len(history.get("epoch", [])) == int(P.train.epochs),
        "new_checkpoint_written":
            CHECKPOINT.exists() and CHECKPOINT.stat().st_size > 0,
        "config_written":
            CONFIG.exists() and CONFIG.stat().st_size > 0,
        "history_written":
            HISTORY.exists() and HISTORY.stat().st_size > 0,

        "holdout_predictions_finite":
            bool(holdout["finite_predictions"]),
        "holdout_saturation_bounds_pass":
            bool(holdout["bounds_pass"]),
        "holdout_mse_finite": finite_number(holdout["mse"]),
        "holdout_mae_finite": finite_number(holdout["mae"]),
        "holdout_max_error_finite": finite_number(holdout["max_abs_error"]),

        "source_case1_metrics_finite": case1_finite,
        "source_case2_metrics_finite": case2_finite,

        "native_coordinate_only": True,
        "TOF_transformation_not_used": True,
        "reproduction_holdout_not_called_OOD": True,
        "no_invented_numeric_acceptance_threshold": True,

        "historical_checkpoint_recovery_claim_false": True,
        "EXP_CS1_not_modified": True,
        "geology0029_not_reopened": True,
    })

    # Manifest is written after metrics/checkpoint hashes exist.
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "status_before_final_gate":
            "NEW_V16E_NATIVE_COORDINATE_REPRODUCTION_COMPLETE_PENDING_GATE_SUMMARY",

        "historical_checkpoint_recovery": False,

        "source": {
            "path": rel(SOURCE),
            "sha256": SOURCE_SHA,
        },

        "upstream_protocol": {
            "E1A_source_sha256": E1A_SOURCE_SHA,
            "protocol_sha256": E1A_PROTOCOL_SHA,
            "issues_sha256": E1A_ISSUES_SHA,
            "artifact_contract_sha256": E1A_ARTIFACTS_SHA,
            "handoff_sha256": E1A_HANDOFF_SHA,
            "summary_sha256": E1A_SUMMARY_SHA,
        },

        "teacher_role":
            "analytical Buckley-Leverett rarefaction + Welge shock/tangent",

        "effective_conditioning_order": list(P.train.condition_on),
        "effective_param_dim": P.param_dim(),
        "sequence_coordinate": "xi = xD / xD_star",

        "architecture": {
            "input_sequence_features": 1,
            "conditioning_dim": P.param_dim(),
            "LSTM_hidden_units": P.train.hidden,
            "LSTM_layers": P.train.layers,
            "output": "TimeDistributed Dense(1) followed by source range map",
        },

        "seed": P.train.seed,
        "train_fraction": 0.8,
        "split_semantics": "source-native reproduction holdout; NOT OOD",

        "dataset_generation_semantics":
            "exact Stage-1 source parameter grid + analytical fan profiles, "
            "six pre-breakthrough times beginning at 100 days",

        "loss_weights": config["loss_weights"],
        "runtime_batch_size": 8192,
        "epochs": P.train.epochs,

        "artifacts": {
            "checkpoint": {
                "path": rel(CHECKPOINT),
                "sha256": sha256(CHECKPOINT),
            },
            "config": {
                "path": rel(CONFIG),
                "sha256": sha256(CONFIG),
            },
            "metrics": {
                "path": rel(METRICS),
                "sha256": sha256(METRICS),
            },
            "training_history": {
                "path": rel(HISTORY),
                "sha256": sha256(HISTORY),
            },
        },

        "diagnostic_figures": {
            "convergence": (
                {"path": rel(CONVERGENCE_PNG), "sha256": sha256(CONVERGENCE_PNG)}
                if CONVERGENCE_PNG.exists() else None
            ),
            "case1": (
                {"path": rel(DIAG1_PNG), "sha256": sha256(DIAG1_PNG)}
                if DIAG1_PNG.exists() else None
            ),
            "case2": (
                {"path": rel(DIAG2_PNG), "sha256": sha256(DIAG2_PNG)}
                if DIAG2_PNG.exists() else None
            ),
        },

        "scientific_firewall": {
            "TOF_transformation": False,
            "OOD_claim": False,
            "EXP_CS1_retrained": False,
            "geology0029_reopened": False,
            "numeric_threshold_invented": False,
        },
    }

    MANIFEST.write_text(
        json.dumps(jsonable(manifest), indent=2),
        encoding="utf-8",
    )

    gates["manifest_written"] = MANIFEST.exists() and MANIFEST.stat().st_size > 0
    gates["manifest_checkpoint_SHA_exact"] = (
        read_json(MANIFEST)["artifacts"]["checkpoint"]["sha256"]
        == sha256(CHECKPOINT)
    )
    gates["manifest_metrics_SHA_exact"] = (
        read_json(MANIFEST)["artifacts"]["metrics"]["sha256"]
        == sha256(METRICS)
    )

    ok = bool(all(bool(v) for v in gates.values()))

    status = (
        "V16E1B1_FINAL_INCOMPRESSIBLE_BL_PI_RNN_NATIVE_COORDINATE_"
        "REPRODUCTION_COMPLETE_NEW_CHECKPOINT_SHA_BOUND_"
        "SOURCE_NATIVE_HOLDOUT_AND_ANALYTICAL_DIAGNOSTICS_FINITE_"
        "SATURATION_BOUNDS_PASS_NO_OOD_CLAIM_"
        "V16E1B2_COMPRESSIBLE_REPRODUCTION_AUTHORIZED"
        if ok else
        "V16E1B1_INCOMPRESSIBLE_REPRODUCTION_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B1",
        "experiment_id": EXPERIMENT_ID,
        "status": status,

        "source_sha256": SOURCE_SHA,
        "checkpoint_sha256": sha256(CHECKPOINT) if CHECKPOINT.exists() else None,
        "config_sha256": sha256(CONFIG) if CONFIG.exists() else None,
        "manifest_sha256": sha256(MANIFEST) if MANIFEST.exists() else None,
        "metrics_sha256": sha256(METRICS) if METRICS.exists() else None,
        "history_sha256": sha256(HISTORY) if HISTORY.exists() else None,

        "holdout_mse": holdout["mse"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mae": holdout["mae"],
        "holdout_max_abs_error": holdout["max_abs_error"],

        "numeric_acceptance_threshold_used": False,
        "OOD_claim": False,
        "TOF_transformation_used": False,

        "next_milestone":
            "V16E-1B2 — Final Compressible BL PI-RNN Native-Coordinate Reproduction"
            if ok else
            "V16E-1B1-R1 — diagnose failed scientific/archival gate without "
            "relabeling this run as successful",

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(
        json.dumps(jsonable(summary), indent=2),
        encoding="utf-8",
    )

    print("\nREPRODUCTION METRICS")
    print(f"  Holdout MSE     : {holdout['mse']:.12e}")
    print(f"  Holdout RMSE    : {holdout['rmse']:.12e}")
    print(f"  Holdout MAE     : {holdout['mae']:.12e}")
    print(f"  Holdout Max |e| : {holdout['max_abs_error']:.12e}")
    print(f"  Bounds violations: "
          f"{holdout['lower_bound_violations'] + holdout['upper_bound_violations']}")

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nARTIFACT HASHES")
    print("  Checkpoint:", sha256(CHECKPOINT) if CHECKPOINT.exists() else None)
    print("  Config    :", sha256(CONFIG) if CONFIG.exists() else None)
    print("  Manifest  :", sha256(MANIFEST) if MANIFEST.exists() else None)
    print("  Metrics   :", sha256(METRICS) if METRICS.exists() else None)
    print("  History   :", sha256(HISTORY) if HISTORY.exists() else None)
    print("  Summary   :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
