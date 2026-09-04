from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-14R
# Independent TOF-Conditioned Candidate Regression Audit
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO PRESERVATION GATE RELAXATION.
# NO TOF-BIAS GATE RELAXATION.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7B-14 independently rejected the SG7B-13 nominated E3 candidate because:
#
#   1. conditioned front gap exceeded the SG7B-10S contract, and
#   2. SG7A/E0-relative front-shape preservation failed,
#
# while all SG7B-12 TOF-bias gates passed.
#
# SG7B-14R therefore evaluates ALL available SG7B-13 E1-E5 best checkpoints
# using the SAME independent validation logic:
#
#   - held-out state / mass / regional gates,
#   - independent canonical physics,
#   - 100-day front recovery / conditioned gap / profile L1,
#   - every SG7B-10S front-shape gate,
#   - every SG7B-12 TOF-bias gate,
#   - the independent ±2.5e-3 500-1000 d overshoot guard.
#
# It answers:
#
#   A. Does an already-trained E1-E5 model satisfy the COMPLETE independent
#      contract?
#
#   B. If not, which preservation gate is the recurring limiting mechanism?
#
# No candidate is frozen here. If a fully passing model exists, SG7B-14R
# nominates it for a fresh SG7B-14B final validation. Otherwise the next
# milestone becomes SG7B-15 front-preserving TOF refinement design.
# =============================================================================


# =============================================================================
# PATHS
# =============================================================================

ROOT = Path(__file__).resolve().parent

SG7B11_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B11_Independent_Front_Aware_Candidate_Validation.py"
)

SG7B10_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B10_Controlled_Front_Aware_Refinement.py"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

SG7B11_PHYSICS_TABLE = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B11_Canonical_Physics_Metrics.csv"
)

SG7B10S_CONTRACT = (
    ROOT / "output" / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B12_CONTRACT = (
    ROOT / "output" / "V15_SG7B12"
    / "V15SG7B12_TOF_Conditioned_Refinement_Contract.json"
)

SG7B13_SUMMARY = (
    ROOT / "output" / "V15_SG7B13"
    / "PAD_Stream_V15SG7B13_Summary.json"
)

SG7B14_SUMMARY = (
    ROOT / "output" / "V15_SG7B14"
    / "PAD_Stream_V15SG7B14_Summary.json"
)

EXPERIMENT_ROOT = (
    ROOT / "output" / "V15_SG7B13" / "experiments"
)

DEFAULT_DEPLOYMENT_WORKSPACE = (
    ROOT.parent / f"{ROOT.name}_SG5C_seed_11x11"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7B14R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_METRICS_FILE = OUTPUT_DIR / "V15SG7B14R_Independent_Model_Metrics.csv"
GATE_MATRIX_FILE = OUTPUT_DIR / "V15SG7B14R_Independent_Gate_Matrix.csv"
SHAPE_MATRIX_FILE = OUTPUT_DIR / "V15SG7B14R_Front_Shape_Gate_Matrix.csv"
FAILURE_COUNTS_FILE = OUTPUT_DIR / "V15SG7B14R_Gate_Failure_Counts.csv"
NOMINATION_FILE = OUTPUT_DIR / "V15SG7B14R_Nomination.json"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7B14R_Summary.json"


# =============================================================================
# GATES
# =============================================================================

MAX_L1 = 0.020
MAX_L2 = 0.030
MAX_MASS_RELATIVE_MAE = 0.030
MAX_CANONICAL_MEAN = 0.500
MAX_CANONICAL_P90 = 1.000
MAX_CANONICAL_FRAC_GT1 = 0.10
MAX_INJECTOR_L1 = 0.015
MAX_FRONT_L1 = 0.030
MAX_EARLY_L1 = 0.020
MAX_LATE_L1 = 0.025

MAX_BIAS_500_1000 = 2.500000e-03
MAX_ABS_BIAS_500_1000 = 2.500000e-03
MAX_BIAS_1000_2000 = 4.500000e-03
MAX_BIAS_GT2000 = 5.000000e-03
MAX_TAIL_BIAS = 5.000000e-03
MAX_500_1000_MATERIAL_SHARE = 0.40

FRONT_THRESHOLD = 0.210
TAIL_LIMIT = 0.205
MATERIAL_POSITIVE_BIAS = 0.005


# =============================================================================
# HELPERS
# =============================================================================

def load_module(path: Path, name: str):
    if not path.exists():
        raise FileNotFoundError(f"Missing source module:\n{path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import module:\n{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def profile_has_crossing(S, threshold=FRONT_THRESHOLD):
    shifted = np.asarray(S, dtype=float) - threshold
    return np.any(shifted[:, :-1] * shifted[:, 1:] < 0.0, axis=1)


def front_metrics(pred, truth):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)

    truth_front = profile_has_crossing(truth)
    pred_front = profile_has_crossing(pred)

    gaps = np.min(np.abs(pred - FRONT_THRESHOLD), axis=1)
    conditioned = gaps[truth_front]

    return {
        "truth_front_count": int(np.sum(truth_front)),
        "recovered_front_count": int(np.sum(truth_front & pred_front)),
        "conditioned_threshold_gap_mean": float(np.mean(conditioned)),
        "profile_L1_mean": float(np.mean(np.abs(pred - truth))),
    }


def bias_metrics(pred, truth, terminal_days):
    pred = np.asarray(pred, dtype=float)
    truth = np.asarray(truth, dtype=float)
    terminal_days = np.asarray(terminal_days, dtype=float)
    error = pred - truth

    def expanded(mask):
        return np.broadcast_to(mask[:, None], error.shape)

    m500 = expanded((terminal_days >= 500.0) & (terminal_days < 1000.0))
    m1000 = expanded((terminal_days >= 1000.0) & (terminal_days < 2000.0))
    m2000 = expanded(terminal_days >= 2000.0)
    tail = truth <= TAIL_LIMIT

    material = error > MATERIAL_POSITIVE_BIAS
    total_material = int(np.sum(material))
    material_500 = int(np.sum(material & m500))

    def mean(mask):
        values = error[mask]
        return float(np.mean(values)) if values.size else np.nan

    return {
        "bias_500_1000": mean(m500),
        "bias_1000_2000": mean(m1000),
        "bias_gt2000": mean(m2000),
        "tail_bias": mean(tail),
        "material_share_500_1000": (
            float(material_500 / total_material)
            if total_material > 0 else 0.0
        ),
        "global_mean_bias": float(np.mean(error)),
        "global_L1": float(np.mean(np.abs(error))),
    }


def get_terminal_days(workspace: Path):
    candidates = [
        workspace / "output" / "V15_SG6" / "STREAMLINE_TRANSPORT_COORDINATES.npz",
        workspace / "output" / "V15_SG6" / "SG6_STREAMLINE_TRANSPORT_COORDINATES.npz",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError(
            "Could not locate SG6 transport-coordinate database.\n"
            + "\n".join(str(p) for p in candidates)
        )
    db = np.load(path, allow_pickle=True)
    for key in ["tau_end_s", "terminal_tau_s", "terminal_tof_s"]:
        if key in db:
            return np.asarray(db[key], dtype=float) / 86400.0
    raise KeyError(f"No terminal TOF key found in {path}")


def load_sg7b11_front_aware_canonical_reference(path: Path):
    rows = load_csv(path)

    accepted = None
    for row in rows:
        label = str(row.get("model", "")).strip()
        if label in {
            "E2_candidate",
            "SG7B11_front_aware_frozen",
            "front_aware_frozen",
        }:
            accepted = row
            break

    if accepted is None:
        raise RuntimeError(
            "Could not identify accepted SG7B-11 front-aware canonical row.\n"
            f"Labels: {[row.get('model') for row in rows]}"
        )

    return {
        "canonical_mean": float(accepted["canonical_mean"]),
        "canonical_P90": float(accepted["canonical_P90"]),
        "fraction_gt_1": float(accepted["fraction_gt_1"]),
        "source_label": str(accepted.get("model", "")),
    }


def relative_close(value, reference, relative_tolerance):
    scale = max(abs(float(reference)), 1.0e-12)
    return abs(float(value) - float(reference)) <= relative_tolerance * scale


def locate_experiment_model(exp: str):
    candidates = [
        EXPERIMENT_ROOT / exp / f"V15SG7B13_{exp}_Best_Model.keras",
        EXPERIMENT_ROOT / exp / f"V15SG7B13_{exp}_Final_Model.keras",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7B-14R independent E1-E5 regression audit."
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default=str(DEFAULT_DEPLOYMENT_WORKSPACE),
        help="Accepted 11x11 SG5C deployment workspace.",
    )
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-14R")
    print("Independent TOF-Conditioned Candidate Regression Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO PRESERVATION GATE WILL BE RELAXED.")
    print("NO TOF-BIAS GATE WILL BE RELAXED.")
    print("NO SG7E PLUME THRESHOLD WILL BE CHANGED.")
    print("NO CANDIDATE WILL BE FROZEN BY SG7B-14R.")

    required = [
        SG7B11_SOURCE,
        SG7B10_SOURCE,
        SG7B11_FROZEN_MODEL,
        SG7B11_PHYSICS_TABLE,
        SG7B10S_CONTRACT,
        SG7B12_CONTRACT,
        SG7B13_SUMMARY,
        SG7B14_SUMMARY,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7B-14R prerequisite:\n{path}")

    sg13_summary = load_json(SG7B13_SUMMARY)
    sg14_summary = load_json(SG7B14_SUMMARY)
    shape_contract = load_json(SG7B10S_CONTRACT)

    if sg13_summary.get("status") != "TOF_CONDITIONED_CANDIDATE_NOMINATED":
        raise RuntimeError("SG7B-14R requires SG7B-13 nominated-candidate status.")

    if sg14_summary.get("status") != "TOF_CONDITIONED_CANDIDATE_VALIDATION_FAILED":
        raise RuntimeError(
            "SG7B-14R requires SG7B-14 failed independent validation status."
        )

    models = {}
    missing = []

    for exp in ["E1", "E2", "E3", "E4", "E5"]:
        path = locate_experiment_model(exp)
        if path is None:
            missing.append(exp)
        else:
            models[exp] = path

    if missing:
        raise FileNotFoundError(
            "Missing SG7B-13 best/final models for:\n"
            + ", ".join(missing)
        )

    print("\nMODEL SET")
    for exp, path in models.items():
        print(
            f"  {exp} | {path.name} | "
            f"SHA-256={sha256_file(path)}"
        )

    # -------------------------------------------------------------------------
    # Authoritative independent modules
    # -------------------------------------------------------------------------
    sg11 = load_module(
        SG7B11_SOURCE,
        "pad_stream_sg7b11_for_sg7b14r",
    )

    sg10 = load_module(
        SG7B10_SOURCE,
        "pad_stream_sg7b10_for_sg7b14r",
    )

    base = sg10.load_base_module()
    tf = sg10.tf

    dataset = base.load_dataset()
    sg7a = base.load_sg7a()
    targets = base.build_advective_targets(dataset, sg7a)

    xi = np.asarray(dataset["xi"], dtype=np.float64)
    tD_scale = float(dataset["tD_scale"][0])

    deployment = sg10.load_deployment_database(
        workspace,
        tD_scale,
    )

    terminal_days = get_terminal_days(workspace)

    # -------------------------------------------------------------------------
    # Independent canonical implementation precheck against SG7B-11 frozen
    # -------------------------------------------------------------------------
    frozen_model = tf.keras.models.load_model(SG7B11_FROZEN_MODEL)

    canonical_truth = sg11.build_sg7a_canonical_reference(
        base,
        tf,
        dataset,
        sg7a,
    )

    frozen_canonical = sg11.canonical_metrics(
        base,
        tf,
        frozen_model,
        dataset,
        canonical_truth,
    )

    reference = load_sg7b11_front_aware_canonical_reference(
        SG7B11_PHYSICS_TABLE
    )

    PRECHECK_REL_TOL = 5.0e-4
    PRECHECK_ABS_TOL_FRAC = 5.0e-5

    precheck_pass = bool(
        relative_close(
            frozen_canonical["canonical_mean"],
            reference["canonical_mean"],
            PRECHECK_REL_TOL,
        )
        and
        relative_close(
            frozen_canonical["canonical_P90"],
            reference["canonical_P90"],
            PRECHECK_REL_TOL,
        )
        and
        abs(
            frozen_canonical["fraction_gt_1"]
            -
            reference["fraction_gt_1"]
        )
        <=
        PRECHECK_ABS_TOL_FRAC
    )

    print("\nINDEPENDENT CANONICAL PRECHECK")
    print(f"  Reference               : {reference['source_label']}")
    print(
        f"  Mean                    : "
        f"{frozen_canonical['canonical_mean']:.6e} "
        f"vs {reference['canonical_mean']:.6e}"
    )
    print(
        f"  P90                     : "
        f"{frozen_canonical['canonical_P90']:.6e} "
        f"vs {reference['canonical_P90']:.6e}"
    )
    print(
        f"  Fraction >1             : "
        f"{100*frozen_canonical['fraction_gt_1']:.3f}% "
        f"vs {100*reference['fraction_gt_1']:.3f}%"
    )
    print(f"  Reproduction            : {'PASS' if precheck_pass else 'FAIL'}")

    if not precheck_pass:
        raise RuntimeError(
            "Independent canonical implementation does not reproduce SG7B-11."
        )

    # -------------------------------------------------------------------------
    # Contracts
    # -------------------------------------------------------------------------
    front_contract = shape_contract["front_improvement_contract"]
    min_fronts = int(front_contract["minimum_recovered_fronts"])
    max_gap = float(front_contract["maximum_conditioned_threshold_gap"])
    max_profile_l1 = float(front_contract["maximum_100d_profile_L1"])

    # -------------------------------------------------------------------------
    # Evaluate all E1-E5
    # -------------------------------------------------------------------------
    model_rows = []
    gate_rows = []
    shape_rows = []
    failure_counter = {}

    for exp, path in models.items():

        print("\n" + "=" * 78)
        print(f"INDEPENDENT EVALUATION — {exp}")
        print("=" * 78)

        model = tf.keras.models.load_model(path)

        test = base.evaluate_split(
            model,
            dataset["X_test"],
            dataset["Y_test"],
            targets["face_test"],
            targets["div_test"],
            xi,
            tD_scale,
        )

        extra = sg10.additional_preservation_metrics(
            dataset["X_test"],
            test["truth"],
            test["prediction"],
        )

        late_key = (
            "late_L1_recomputed"
            if "late_L1_recomputed" in extra
            else "late_L1"
        )

        canonical = sg11.canonical_metrics(
            base,
            tf,
            model,
            dataset,
            canonical_truth,
        )

        pred100 = model.predict(
            deployment["X100"],
            batch_size=sg10.BATCH_SIZE,
            verbose=0,
        )[:, :, 0]

        front = front_metrics(
            pred100,
            deployment["truth100"],
        )

        bias = bias_metrics(
            pred100,
            deployment["truth100"],
            terminal_days,
        )

        local_mask = sg11.front_pair_mask(
            deployment["truth100"],
            sg10.FRONT_HIGH,
            sg10.CROSSING_LOW,
        )

        shape = sg11.local_shape_metrics(
            pred100,
            deployment["truth100"],
            deployment["xi"],
            local_mask,
            sg10.MONOTONIC_TOL,
        )

        shape_pass = True

        for gate in shape_contract["shape_preservation_gates"]:
            gate_name = str(gate["gate"])
            value = float(shape[gate_name])
            limit = float(gate["candidate_limit"])
            passed = bool(value <= limit)

            shape_rows.append({
                "experiment": exp,
                "gate": gate_name,
                "value": value,
                "limit": limit,
                "passed": passed,
                "ratio_to_limit": (
                    value / limit
                    if abs(limit) > 0.0
                    else np.nan
                ),
            })

            shape_pass = shape_pass and passed

        gates = [
            ("finite", bool(np.all(np.isfinite(test["prediction"])) and np.all(np.isfinite(pred100)))),
            ("saturation_lower", bool(test["minimum_prediction"] >= base.S_INITIAL - 1e-7)),
            ("saturation_upper", bool(test["maximum_prediction"] <= base.S_INJECTED + 1e-7)),
            ("heldout_L1", bool(test["L1"] < MAX_L1)),
            ("heldout_L2", bool(test["L2"] < MAX_L2)),
            ("mass_relative_MAE", bool(test["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE)),
            ("canonical_mean", bool(canonical["canonical_mean"] < MAX_CANONICAL_MEAN)),
            ("canonical_P90", bool(canonical["canonical_P90"] < MAX_CANONICAL_P90)),
            ("canonical_fraction_gt1", bool(canonical["fraction_gt_1"] < MAX_CANONICAL_FRAC_GT1)),
            ("injector_L1", bool(test["injector_L1"] < MAX_INJECTOR_L1)),
            ("front_L1", bool(extra["front_L1"] < MAX_FRONT_L1)),
            ("early_L1", bool(extra["early_L1"] < MAX_EARLY_L1)),
            ("late_L1", bool(extra[late_key] < MAX_LATE_L1)),
            ("recovered_fronts", bool(front["recovered_front_count"] >= min_fronts)),
            ("conditioned_front_gap", bool(front["conditioned_threshold_gap_mean"] <= max_gap)),
            ("profile_100d_L1", bool(front["profile_L1_mean"] <= max_profile_l1)),
            ("relative_front_shape", bool(shape_pass)),
            ("bias_500_1000", bool(bias["bias_500_1000"] <= MAX_BIAS_500_1000)),
            ("abs_bias_500_1000", bool(abs(bias["bias_500_1000"]) <= MAX_ABS_BIAS_500_1000)),
            ("bias_1000_2000", bool(bias["bias_1000_2000"] <= MAX_BIAS_1000_2000)),
            ("bias_gt2000", bool(bias["bias_gt2000"] <= MAX_BIAS_GT2000)),
            ("tail_bias", bool(bias["tail_bias"] <= MAX_TAIL_BIAS)),
            ("material_share_500_1000", bool(bias["material_share_500_1000"] <= MAX_500_1000_MATERIAL_SHARE)),
        ]

        complete_pass = all(flag for _, flag in gates)

        for name, flag in gates:
            gate_rows.append({
                "experiment": exp,
                "gate": name,
                "passed": bool(flag),
            })
            if not flag:
                failure_counter[name] = failure_counter.get(name, 0) + 1

        model_row = {
            "experiment": exp,
            "model": path.name,
            "sha256": sha256_file(path),
            "complete_independent_pass": bool(complete_pass),

            "heldout_L1": test["L1"],
            "heldout_L2": test["L2"],
            "heldout_Linf": test["Linf"],
            "mass_relative_MAE": test["mass_relative_MAE"],
            "injector_L1": test["injector_L1"],
            "front_L1": extra["front_L1"],
            "early_L1": extra["early_L1"],
            "late_L1": extra[late_key],

            "canonical_mean": canonical["canonical_mean"],
            "canonical_P90": canonical["canonical_P90"],
            "canonical_fraction_gt1": canonical["fraction_gt_1"],

            "recovered_fronts": front["recovered_front_count"],
            "truth_fronts": front["truth_front_count"],
            "conditioned_front_gap": front["conditioned_threshold_gap_mean"],
            "profile_100d_L1": front["profile_L1_mean"],
            "front_shape_pass": bool(shape_pass),

            "bias_500_1000": bias["bias_500_1000"],
            "abs_bias_500_1000": abs(bias["bias_500_1000"]),
            "bias_1000_2000": bias["bias_1000_2000"],
            "bias_gt2000": bias["bias_gt2000"],
            "tail_bias": bias["tail_bias"],
            "material_share_500_1000": bias["material_share_500_1000"],
        }

        model_rows.append(model_row)

        print(f"  Complete pass           : {complete_pass}")
        print(f"  Recovered fronts        : {front['recovered_front_count']} / {front['truth_front_count']}")
        print(f"  Conditioned gap         : {front['conditioned_threshold_gap_mean']:.6e} / {max_gap:.6e}")
        print(f"  Front-shape pass        : {shape_pass}")
        print(f"  500-1000d bias          : {bias['bias_500_1000']:.6e}")
        print(f"  1000-2000d bias         : {bias['bias_1000_2000']:.6e}")
        print(f"  >2000d bias             : {bias['bias_gt2000']:.6e}")
        print(f"  Tail bias               : {bias['tail_bias']:.6e}")

        failed = [name for name, flag in gates if not flag]
        print(
            f"  Failed gates            : "
            f"{', '.join(failed) if failed else 'NONE'}"
        )

    # -------------------------------------------------------------------------
    # Selection logic
    # -------------------------------------------------------------------------
    passing = [
        row for row in model_rows
        if row["complete_independent_pass"]
    ]

    if passing:
        # Best fully passing candidate:
        # prioritize small absolute 500-1000 d bias, then front gap, then L1.
        passing.sort(
            key=lambda row: (
                row["abs_bias_500_1000"],
                row["conditioned_front_gap"],
                row["heldout_L1"],
            )
        )

        winner = passing[0]

        status = "EXISTING_SG7B13_CANDIDATE_PASSES_COMPLETE_INDEPENDENT_CONTRACT"
        diagnosis = "ALTERNATE_EXISTING_CANDIDATE_RESOLVES_TRADEOFF"

        recommendation = (
            f"{winner['experiment']} independently satisfies the complete "
            "SG7B-11 state/mass/canonical contract, SG7B-10S front-shape "
            "contract, SG7B-12 TOF-bias contract, and the 500-1000 d "
            "overshoot guard. Do not retrain. Proceed to a clean final "
            "validation/freeze using this alternate existing checkpoint."
        )

        next_milestone = (
            "V15-SG7B-14B — Final Validation of Alternate TOF-Conditioned Candidate"
        )

        nomination = {
            "milestone": "V15-SG7B-14R",
            "status": status,
            "experiment": winner["experiment"],
            "model": str(models[winner["experiment"]]),
            "sha256": winner["sha256"],
            "complete_independent_pass": True,
            "candidate_is_frozen": False,
            "next_milestone": next_milestone,
        }

    else:
        winner = None

        # Diagnose recurring independent failure modes.
        recurring = sorted(
            failure_counter.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )

        top_gate = recurring[0][0] if recurring else "unknown"
        top_count = recurring[0][1] if recurring else 0

        if (
            failure_counter.get("conditioned_front_gap", 0) >= 3
            or
            failure_counter.get("relative_front_shape", 0) >= 3
        ):
            diagnosis = "TOF_REFINEMENT_FRONT_PRESERVATION_TRADEOFF"
            next_milestone = (
                "V15-SG7B-15 — Front-Preserving TOF Refinement Design"
            )
            recommendation = (
                "No existing E1-E5 checkpoint independently satisfies the "
                "complete contract. Front-position/shape preservation is a "
                "recurring limiting mechanism, so do not relax gates and do "
                "not reuse E3. Design a narrower TOF correction with stronger "
                "front anchoring and explicitly bounded front displacement."
            )
        else:
            diagnosis = "MULTI_GATE_TOF_REFINEMENT_REGRESSION"
            next_milestone = (
                "V15-SG7B-15 — Multi-Constraint TOF Refinement Redesign"
            )
            recommendation = (
                "No existing E1-E5 checkpoint independently satisfies the "
                "complete contract. The failures are not dominated by a single "
                "front-preservation mechanism; redesign the controlled loss "
                "with the observed independent failure matrix."
            )

        status = "NO_EXISTING_SG7B13_CANDIDATE_PASSES_COMPLETE_INDEPENDENT_CONTRACT"

        nomination = {
            "milestone": "V15-SG7B-14R",
            "status": status,
            "experiment": None,
            "model": None,
            "sha256": None,
            "complete_independent_pass": False,
            "dominant_failed_gate": top_gate,
            "dominant_failed_gate_count": top_count,
            "next_milestone": next_milestone,
        }

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------
    save_csv(MODEL_METRICS_FILE, model_rows)
    save_csv(GATE_MATRIX_FILE, gate_rows)
    save_csv(SHAPE_MATRIX_FILE, shape_rows)

    failure_rows = [
        {
            "gate": gate,
            "failed_experiments": count,
            "failure_fraction": count / len(models),
        }
        for gate, count in sorted(
            failure_counter.items(),
            key=lambda kv: (-kv[1], kv[0]),
        )
    ]
    save_csv(FAILURE_COUNTS_FILE, failure_rows)
    save_json(NOMINATION_FILE, nomination)

    summary = {
        "milestone": "V15-SG7B-14R",
        "status": status,
        "diagnosis": diagnosis,
        "models_evaluated": list(models.keys()),
        "passing_models": [row["experiment"] for row in passing],
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }
    save_json(SUMMARY_FILE, summary)

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------
    labels = [row["experiment"] for row in model_rows]

    plt.figure(figsize=(9, 5))
    plt.bar(
        labels,
        [row["conditioned_front_gap"] for row in model_rows],
    )
    plt.axhline(max_gap, linestyle="--")
    plt.ylabel("Conditioned front gap")
    plt.xlabel("Experiment")
    plt.title("V15-SG7B-14R independent conditioned-front-gap audit")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7B14R_Conditioned_Front_Gap.png",
        dpi=300,
    )
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.bar(
        labels,
        [row["bias_500_1000"] for row in model_rows],
    )
    plt.axhline(MAX_BIAS_500_1000, linestyle="--")
    plt.axhline(-MAX_ABS_BIAS_500_1000, linestyle="--")
    plt.ylabel("500-1000 d mean bias")
    plt.xlabel("Experiment")
    plt.title("V15-SG7B-14R independent TOF-bias comparison")
    plt.tight_layout()
    plt.savefig(
        OUTPUT_DIR / "V15SG7B14R_Bias_500_1000.png",
        dpi=300,
    )
    plt.close()

    if failure_rows:
        plt.figure(figsize=(10, 6))
        plt.bar(
            [row["gate"] for row in failure_rows],
            [row["failed_experiments"] for row in failure_rows],
        )
        plt.ylabel("Number of failed E1-E5 models")
        plt.xlabel("Independent gate")
        plt.title("V15-SG7B-14R recurring independent failures")
        plt.xticks(rotation=60, ha="right")
        plt.tight_layout()
        plt.savefig(
            OUTPUT_DIR / "V15SG7B14R_Gate_Failure_Counts.png",
            dpi=300,
        )
        plt.close()

    # -------------------------------------------------------------------------
    # Print final
    # -------------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("V15-SG7B-14R REGRESSION AUDIT")
    print("=" * 78)

    for row in model_rows:
        print(
            f"[{'PASS' if row['complete_independent_pass'] else 'FAIL'}] "
            f"{row['experiment']} | "
            f"gap={row['conditioned_front_gap']:.3e} | "
            f"shape={'PASS' if row['front_shape_pass'] else 'FAIL'} | "
            f"B500={row['bias_500_1000']:.3e} | "
            f"B1000={row['bias_1000_2000']:.3e} | "
            f"B2000={row['bias_gt2000']:.3e} | "
            f"tail={row['tail_bias']:.3e}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    if winner is not None:
        print("\nALTERNATE CANDIDATE")
        print(f"  Experiment              : {winner['experiment']}")
        print(f"  Model                   : {models[winner['experiment']].name}")
        print(f"  SHA-256                 : {winner['sha256']}")
    else:
        print("\nRECURRING FAILED GATES")
        if failure_rows:
            for row in failure_rows:
                print(
                    f"  {row['gate']:<32s}: "
                    f"{row['failed_experiments']} / {len(models)}"
                )
        else:
            print("  None recorded")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")

    print("\nTables:")
    print(f"  {MODEL_METRICS_FILE.name}")
    print(f"  {GATE_MATRIX_FILE.name}")
    print(f"  {SHAPE_MATRIX_FILE.name}")
    print(f"  {FAILURE_COUNTS_FILE.name}")

    print("\nNomination:")
    print(f"  {NOMINATION_FILE.name}")

    print("\nDiagnostics:")
    print("  V15SG7B14R_Conditioned_Front_Gap.png")
    print("  V15SG7B14R_Bias_500_1000.png")
    print("  V15SG7B14R_Gate_Failure_Counts.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7B-14R AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No preservation or TOF-bias gate was changed.")
    print("No candidate was frozen.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
