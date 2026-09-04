#!/usr/bin/env python3
"""
PAD-Stream V16E-1B1-XPU-R1
Post-Training Evaluation Repair

Repairs ONLY the failed evaluation phase of V16E-BLREP-INC-XPU-001.

The full 400-epoch XPU training already completed and wrote the checkpoint,
config, protocol, and history. The original evaluator failed because the model
remained in PyTorch train mode; Intel oneDNN XPU LSTM inference requires
model.eval().

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO TOF.
NO OOD.
"""

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys
import time

import numpy as np
import torch


R = Path(__file__).resolve().parent
EXPERIMENT_ID = "V16E-BLREP-INC-XPU-001"

RUNNER = R / "PAD_Stream_V16E1B1_XPU_Final_Incompressible_BL_PIRNN_Native_Coordinate_Reproduction.py"
RUNNER_SHA = "d5925a5b5e7e2591142596cb5f13eed4d16507dad534ae334cae646e7ffc3435"

STAGE1 = R / "pi_rnn_stage1_incompressible.py"
STAGE1_SHA = "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58"

DATASET = R / "output" / "V16_E1B_XPU_DATASETS" / "V16E_STAGE1_ANALYTICAL_FAN_DATASET_SEED1337.npz"
DATASET_META = R / "output" / "V16_E1B_XPU_DATASETS" / "V16E_STAGE1_ANALYTICAL_FAN_DATASET_SEED1337.json"
DATASET_SHA = "3495f933a377928254465d60ed5452bcb9fb0fdf6a9507efab94edd4abee6e98"

OUT = R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS" / EXPERIMENT_ID
CHECKPOINT = OUT / "V16E_BLREP_INC_XPU_001.pt"
CONFIG = OUT / "V16E_BLREP_INC_XPU_001_Config.json"
PORT_PROTOCOL = OUT / "V16E_BLREP_INC_XPU_001_Framework_Port_Protocol.json"
HISTORY = OUT / "V16E_BLREP_INC_XPU_001_Training_History.json"

METRICS = OUT / "V16E_BLREP_INC_XPU_001_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_INC_XPU_001_Manifest.json"
REPAIR = OUT / "V16E_BLREP_INC_XPU_001_R1_Evaluation_Repair.json"
SUMMARY = OUT / "PAD_Stream_V16E1B1_XPU_R1_Summary.json"
ORIGINAL_SUMMARY = OUT / "PAD_Stream_V16E1B1_XPU_Summary.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path):
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def finite(x):
    try:
        return math.isfinite(float(x))
    except Exception:
        return False


def import_runner():
    spec = importlib.util.spec_from_file_location("v16e1b1_xpu_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import frozen XPU runner.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rows_finite(case):
    rows = case.get("rows", [])
    return len(rows) == 15 and all(
        finite(r.get("mse"))
        and finite(r.get("mae"))
        and finite(r.get("max_abs_err"))
        for r in rows
    )


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B1-XPU-R1")
    print("Post-Training Evaluation Repair")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print("NO TRAINING — existing checkpoint only.\n")

    if SUMMARY.exists():
        raise RuntimeError("R1 summary already exists; refusing overwrite.")

    gates = {
        "runner_SHA_exact": exact(RUNNER, RUNNER_SHA),
        "Stage1_SHA_exact": exact(STAGE1, STAGE1_SHA),
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "dataset_meta_exists": DATASET_META.exists(),
        "checkpoint_exists": CHECKPOINT.exists() and CHECKPOINT.stat().st_size > 0,
        "config_exists": CONFIG.exists() and CONFIG.stat().st_size > 0,
        "port_protocol_exists": PORT_PROTOCOL.exists() and PORT_PROTOCOL.stat().st_size > 0,
        "history_exists": HISTORY.exists() and HISTORY.stat().st_size > 0,
        "original_summary_absent": not ORIGINAL_SUMMARY.exists(),
        "old_metrics_absent": not METRICS.exists(),
        "old_manifest_absent": not MANIFEST.exists(),
    }

    print("PRE-REPAIR GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)
    if not all(gates.values()):
        raise RuntimeError("Expected post-training/pre-evaluation state not found.")

    cfg = load_json(CONFIG)
    hist = load_json(HISTORY)
    proto = load_json(PORT_PROTOCOL)
    dsmeta = load_json(DATASET_META)

    gates.update({
        "config_experiment_exact": cfg.get("experiment_id") == EXPERIMENT_ID,
        "config_full_run": cfg.get("full_certification_run") is True,
        "config_epochs_400": cfg.get("epochs_requested") == 400,
        "config_microbatch_2048": cfg.get("microbatch") == 2048,
        "config_param_dim_10": cfg.get("param_dim") == 10,
        "config_hidden_64": cfg.get("hidden") == 64,
        "config_layers_2": cfg.get("layers") == 2,
        "config_seed_1337": cfg.get("seed") == 1337,
        "config_dataset_SHA_exact": cfg.get("dataset", {}).get("sha256") == DATASET_SHA,
        "config_source_SHA_exact": cfg.get("source_sha256") == STAGE1_SHA,
        "protocol_experiment_exact": proto.get("experiment_id") == EXPERIMENT_ID,
        "protocol_framework_equivalent":
            proto.get("classification") == "FRAMEWORK_EQUIVALENT_ACCELERATION_PORT",
        "history_400_epochs":
            isinstance(hist.get("epoch"), list)
            and len(hist["epoch"]) == 400
            and hist["epoch"][0] == 1
            and hist["epoch"][-1] == 400,
        "dataset_meta_source_SHA_exact": dsmeta.get("source_sha256") == STAGE1_SHA,
        "dataset_meta_SHA_exact": dsmeta.get("dataset_sha256") == DATASET_SHA,
        "dataset_meta_profiles_155520": dsmeta.get("profile_count") == 155520,
    })

    for key in ("data", "physics", "bc_inj", "bc_tip", "anchor", "mono", "shape", "total"):
        vals = hist.get(key)
        gates[f"history_{key}_finite"] = (
            isinstance(vals, list)
            and len(vals) == 400
            and all(finite(v) for v in vals)
        )

    print("\nCOMPLETED TRAINING PROOF")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)
    if not all(gates.values()):
        raise RuntimeError("Saved artifacts do not prove a complete frozen 400-epoch run.")

    checkpoint_sha = sha256(CHECKPOINT)

    print("\nLOADING EXISTING CHECKPOINT")
    M = import_runner()

    print("PyTorch:", torch.__version__)
    print("XPU available:", torch.xpu.is_available())
    if not torch.xpu.is_available():
        raise RuntimeError("XPU unavailable.")

    payload = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)

    gates.update({
        "checkpoint_experiment_exact": payload.get("experiment_id") == EXPERIMENT_ID,
        "checkpoint_source_SHA_exact": payload.get("source_sha256") == STAGE1_SHA,
        "checkpoint_param_dim_10": payload.get("param_dim") == 10,
        "checkpoint_hidden_64": payload.get("hidden") == 64,
        "checkpoint_layers_2": payload.get("layers") == 2,
        "checkpoint_framework_XPU": payload.get("framework") == "PyTorch XPU",
    })

    device = torch.device("xpu")
    model = M.PIRNNFanXPU()
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.to(device)

    # Minimal repair:
    model.eval()

    gates.update({
        "model_eval_mode_active": model.training is False,
        "model_parameters_on_XPU": {p.device.type for p in model.parameters()} == {"xpu"},
        "checkpoint_SHA_unchanged_after_load": sha256(CHECKPOINT) == checkpoint_sha,
    })

    if not all(gates.values()):
        raise RuntimeError("Checkpoint/model binding failed.")

    print("\nLOADING FROZEN DATASET")
    d = np.load(DATASET)
    arrays = (d["xi"], d["Sw"], d["p10"], d["tD"], d["ai"], d["at"])
    xi, Sw, p10, tD, ai, at = arrays

    rng = np.random.default_rng(1337)
    idx = np.arange(len(xi))
    rng.shuffle(idx)
    n_train = int(0.8 * len(idx))
    holdout_idx = idx[n_train:]

    gates.update({
        "xi_shape_exact": tuple(xi.shape) == (155520, 112, 1),
        "Sw_shape_exact": tuple(Sw.shape) == (155520, 112, 1),
        "p10_shape_exact": tuple(p10.shape) == (155520, 10),
        "holdout_count_31104": len(holdout_idx) == 31104,
    })
    if not all(gates.values()):
        raise RuntimeError("Dataset/split binding failed.")

    print("\nSOURCE-NATIVE HOLDOUT EVALUATION")
    t0 = time.time()
    holdout = M.holdout_metrics(model, arrays, holdout_idx, device)

    print(f"  MSE     : {holdout['mse']:.12e}")
    print(f"  RMSE    : {holdout['rmse']:.12e}")
    print(f"  MAE     : {holdout['mae']:.12e}")
    print(f"  Max |e| : {holdout['max_abs_error']:.12e}")
    print("  Bounds  :", "PASS" if holdout["bounds_pass"] else "FAIL")

    p1 = M.make_case_from_values(
        M.BASE_P, no=2.0, nw=2.0, swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7, phi=0.20
    )
    p2 = M.make_case_from_values(
        M.BASE_P, no=3.0, nw=2.0, swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9, phi=0.25
    )

    print("\nSOURCE ANALYTICAL CASE DIAGNOSTICS")
    case1 = M.evaluate_case(model, p1, device)
    case2 = M.evaluate_case(model, p2, device)
    eval_seconds = time.time() - t0

    print("  Case 1 R2:", f"{case1['diagnostics']['r_squared']:.8f}")
    print("  Case 2 R2:", f"{case2['diagnostics']['r_squared']:.8f}")

    gates.update({
        "holdout_predictions_finite": holdout["finite_predictions"],
        "holdout_bounds_pass": holdout["bounds_pass"],
        "holdout_metrics_finite":
            all(finite(holdout[k]) for k in ("mse", "rmse", "mae", "max_abs_error")),
        "case1_rows_finite": rows_finite(case1),
        "case2_rows_finite": rows_finite(case2),
        "case1_diagnostics_finite":
            finite(case1["diagnostics"]["r_squared"])
            and finite(case1["diagnostics"]["max_abs_residual"]),
        "case2_diagnostics_finite":
            finite(case2["diagnostics"]["r_squared"])
            and finite(case2["diagnostics"]["max_abs_residual"]),
        "training_not_executed_in_R1": True,
        "optimizer_not_created_in_R1": True,
        "checkpoint_not_modified": sha256(CHECKPOINT) == checkpoint_sha,
        "no_TOF": True,
        "no_OOD": True,
        "no_threshold_invented": True,
    })

    metrics = {
        "milestone": "V16E-1B1-XPU-R1",
        "experiment_id": EXPERIMENT_ID,
        "classification": "POST_TRAINING_EVALUATION_ONLY_REPAIR",
        "checkpoint_sha256": checkpoint_sha,
        "epochs_reused": 400,
        "training_repeated": False,
        "final_logged_losses": {
            k: hist[k][-1]
            for k in ("data", "physics", "bc_inj", "bc_tip", "anchor", "mono", "shape", "total")
        },
        "dataset_sha256": DATASET_SHA,
        "holdout": holdout,
        "case_1_symmetric": case1,
        "case_2_asymmetric": case2,
        "evaluation_seconds": eval_seconds,
        "threshold_policy": "No numerical threshold invented or applied.",
    }
    METRICS.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    repair = {
        "milestone": "V16E-1B1-XPU-R1",
        "experiment_id": EXPERIMENT_ID,
        "failure": "oneDNN LSTM on XPU only supports inference mode",
        "root_cause":
            "torch.no_grad() disabled gradient recording but the module remained in train mode.",
        "repair": "Loaded existing checkpoint and called model.eval() before inference.",
        "training_repeated": False,
        "weights_modified": False,
        "checkpoint_sha256_before": checkpoint_sha,
        "checkpoint_sha256_after": sha256(CHECKPOINT),
        "checkpoint_unchanged": sha256(CHECKPOINT) == checkpoint_sha,
    }
    REPAIR.write_text(json.dumps(repair, indent=2), encoding="utf-8")

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "certification_milestone": "V16E-1B1-XPU-R1",
        "classification":
            "FRAMEWORK_EQUIVALENT_XPU_REPRODUCTION_POSTTRAINING_REPAIR_CERTIFIED",
        "source_sha256": STAGE1_SHA,
        "runner_sha256": RUNNER_SHA,
        "dataset_sha256": DATASET_SHA,
        "checkpoint_sha256": checkpoint_sha,
        "config_sha256": sha256(CONFIG),
        "port_protocol_sha256": sha256(PORT_PROTOCOL),
        "history_sha256": sha256(HISTORY),
        "metrics_sha256": sha256(METRICS),
        "repair_sha256": sha256(REPAIR),
        "framework": "PyTorch XPU",
        "model_eval_used": True,
        "training_repeated_in_R1": False,
        "weights_modified_in_R1": False,
        "OOD_claim": False,
        "TOF": False,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    gates.update({
        "metrics_written": METRICS.exists() and METRICS.stat().st_size > 0,
        "repair_written": REPAIR.exists() and REPAIR.stat().st_size > 0,
        "manifest_written": MANIFEST.exists() and MANIFEST.stat().st_size > 0,
        "repair_checkpoint_unchanged": load_json(REPAIR)["checkpoint_unchanged"] is True,
        "manifest_checkpoint_SHA_exact": load_json(MANIFEST)["checkpoint_sha256"] == checkpoint_sha,
        "manifest_metrics_SHA_exact": load_json(MANIFEST)["metrics_sha256"] == sha256(METRICS),
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B1_XPU_R1_POSTTRAINING_EVALUATION_REPAIR_CERTIFIED_"
        "FULL_400_EPOCH_XPU_TRAINING_PRESERVED_CHECKPOINT_UNCHANGED_"
        "MODEL_EVAL_INFERENCE_REPAIR_APPLIED_"
        "SOURCE_NATIVE_HOLDOUT_AND_ANALYTICAL_DIAGNOSTICS_FINITE_"
        "SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
        "V16E1B2_XPU_COMPRESSIBLE_PORT_AUTHORIZED"
        if ok else
        "V16E1B1_XPU_R1_EVALUATION_REPAIR_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B1-XPU-R1",
        "experiment_id": EXPERIMENT_ID,
        "status": status,
        "checkpoint_sha256": checkpoint_sha,
        "config_sha256": sha256(CONFIG),
        "port_protocol_sha256": sha256(PORT_PROTOCOL),
        "history_sha256": sha256(HISTORY),
        "metrics_sha256": sha256(METRICS),
        "repair_sha256": sha256(REPAIR),
        "manifest_sha256": sha256(MANIFEST),
        "holdout_mse": holdout["mse"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mae": holdout["mae"],
        "holdout_max_abs_error": holdout["max_abs_error"],
        "case1_r_squared": case1["diagnostics"]["r_squared"],
        "case2_r_squared": case2["diagnostics"]["r_squared"],
        "training_repeated_in_R1": False,
        "weights_modified_in_R1": False,
        "next_milestone":
            "V16E-1B2-XPU — Final Compressible BL PI-RNN framework-equivalent "
            "native-coordinate XPU port/reproduction"
            if ok else
            "V16E-1B1-XPU-R2 — diagnose remaining evaluation gate",
        "gates": {k: bool(v) for k, v in gates.items()},
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nFINAL REPAIR GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nARTIFACT HASHES")
    print("  Checkpoint:", checkpoint_sha)
    print("  Metrics   :", sha256(METRICS))
    print("  Repair    :", sha256(REPAIR))
    print("  Manifest  :", sha256(MANIFEST))
    print("  Summary   :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
