from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil

import numpy as np
import matplotlib.pyplot as plt


# =============================================================================
# PAD-Stream V15-SG7B-14
# Independent TOF-Conditioned Candidate Validation
#
# NO TRAINING.
# NO ARCHITECTURE CHANGE.
# NO SG7B-11 GATE RELAXATION.
# NO SG7B-12 BIAS-GATE RELAXATION.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# Independently validate the SG7B-13 nominated candidate (E3) against:
#
#   A. complete SG7B-7R / SG7B-11 state, mass, regional, saturation-bound,
#      and canonical-physics contract;
#   B. SG7B-10S front recovery + SG7A/E0-relative front-shape contract;
#   C. SG7B-12 TOF-conditioned residual-bias contract;
#   D. a new overshoot guard so the 500-1000 d correction cannot simply trade
#      the original positive bias for an excessive negative bias.
#
# Only if every independent gate passes is a NEW TOF-conditioned frozen model
# created. The SG7B-11 frozen model remains archived and unchanged.
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

SG7B13_SOURCE = (
    ROOT / "PAD_Stream_V15SG7B13_Controlled_TOF_Conditioned_Residual_Bias_Refinement.py"
)

SG7B13_SUMMARY = (
    ROOT / "output" / "V15_SG7B13" / "PAD_Stream_V15SG7B13_Summary.json"
)

SG7B13_MANIFEST = (
    ROOT / "output" / "V15_SG7B13" / "V15SG7B13_Candidate_Manifest.json"
)

CANDIDATE_MODEL = (
    ROOT / "output" / "V15_SG7B13" / "V15SG7B13_Candidate_Model.keras"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11" / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

# IMPORTANT:
# SG7B-14 starts from the SG7B-11 FRONT-AWARE frozen model, not the older
# SG7B-7R frozen model. Therefore the independent canonical implementation
# must reproduce the canonical metrics that were actually recorded when
# SG7B-11 froze the front-aware model.
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

DEFAULT_DEPLOYMENT_WORKSPACE = (
    ROOT.parent / f"{ROOT.name}_SG5C_seed_11x11"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7B14"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FROZEN_MODEL = OUTPUT_DIR / "V15SG7B_TOF_CONDITIONED_FROZEN_Model.keras"
FREEZE_MANIFEST = OUTPUT_DIR / "V15SG7B14_TOF_Conditioned_Freeze_Manifest.json"
GATE_TABLE = OUTPUT_DIR / "V15SG7B14_Final_Gates.csv"
PHYSICS_TABLE = OUTPUT_DIR / "V15SG7B14_Canonical_Physics_Metrics.csv"
REGIONAL_TABLE = OUTPUT_DIR / "V15SG7B14_State_Regional_Metrics.csv"
BIAS_TABLE = OUTPUT_DIR / "V15SG7B14_TOF_Bias_Metrics.csv"
SHAPE_TABLE = OUTPUT_DIR / "V15SG7B14_Front_Shape_Metrics.csv"
NUMERICAL_FILE = OUTPUT_DIR / "V15SG7B14_Final_Validation.npz"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7B14_Summary.json"


# =============================================================================
# RETAINED GATES
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

# SG7B-12
MAX_BIAS_500_1000 = 2.500000e-03
MAX_BIAS_1000_2000 = 4.500000e-03
MAX_BIAS_GT2000 = 5.000000e-03
MAX_TAIL_BIAS = 5.000000e-03
MAX_500_1000_MATERIAL_SHARE = 0.40

# Independent overshoot guard: the targeted 500-1000 d mean residual must
# remain inside the same ±2.5e-3 envelope, not merely be less than +2.5e-3.
MAX_ABS_BIAS_500_1000 = 2.500000e-03

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


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing CSV:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_sg7b11_front_aware_canonical_reference(path: Path):
    """
    Read the canonical metrics of the model that SG7B-11 actually accepted
    and froze.

    SG7B-11's table contains:
      - E0_frozen_precheck : the older SG7B-7R frozen baseline
      - E2_candidate       : the front-aware candidate that became the
                             authoritative SG7B-11 frozen model

    SG7B-14 must reproduce E2_candidate, not E0_frozen_precheck.
    """
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
            "Could not identify the accepted SG7B-11 front-aware canonical "
            "reference row in:\n"
            f"{path}\n"
            f"Available model labels: {[row.get('model') for row in rows]}"
        )

    required = [
        "canonical_mean",
        "canonical_P90",
        "fraction_gt_1",
    ]

    for key in required:
        if key not in accepted:
            raise KeyError(
                f"SG7B-11 canonical table is missing field '{key}'."
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


def independent_front_metrics(pred, truth):
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


def independent_bias_metrics(pred, truth, terminal_days):
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
    sg6_path = next((p for p in candidates if p.exists()), None)
    if sg6_path is None:
        raise FileNotFoundError(
            "Could not locate SG6 transport-coordinate database.\n"
            + "\n".join(str(p) for p in candidates)
        )
    db = np.load(sg6_path, allow_pickle=True)
    for key in ["tau_end_s", "terminal_tau_s", "terminal_tof_s"]:
        if key in db:
            return np.asarray(db[key], dtype=float) / 86400.0
    raise KeyError(f"No terminal TOF key found in {sg6_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PAD-Stream V15-SG7B-14 independent TOF-conditioned candidate validation."
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
    print("PAD-Stream Version 15-SG7B-14")
    print("Independent TOF-Conditioned Candidate Validation")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO SG7B-11 GATE WILL BE RELAXED.")
    print("NO SG7B-12 BIAS GATE WILL BE RELAXED.")
    print("NO SG7E PLUME THRESHOLD WILL BE CHANGED.")
    print("THE SG7B-11 FROZEN MODEL WILL NOT BE OVERWRITTEN.")

    required = [
        SG7B11_SOURCE, SG7B10_SOURCE, SG7B13_SOURCE,
        SG7B13_SUMMARY, SG7B13_MANIFEST, CANDIDATE_MODEL,
        SG7B11_FROZEN_MODEL, SG7B11_PHYSICS_TABLE,
        SG7B10S_CONTRACT, SG7B12_CONTRACT,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7B-14 prerequisite:\n{path}")

    sg13_summary = load_json(SG7B13_SUMMARY)
    sg13_manifest = load_json(SG7B13_MANIFEST)
    sg10s_contract = load_json(SG7B10S_CONTRACT)
    sg12_contract = load_json(SG7B12_CONTRACT)

    if sg13_summary.get("status") != "TOF_CONDITIONED_CANDIDATE_NOMINATED":
        raise RuntimeError("SG7B-14 requires SG7B-13 nominated-candidate status.")

    candidate_hash = sha256_file(CANDIDATE_MODEL)
    if candidate_hash != sg13_manifest.get("candidate_sha256"):
        raise RuntimeError(
            "SG7B-13 candidate SHA-256 does not match candidate manifest."
        )

    frozen_hash = sha256_file(SG7B11_FROZEN_MODEL)

    print("\nMODEL IDENTITY")
    print(f"  SG7B-11 frozen model    : {SG7B11_FROZEN_MODEL.name}")
    print(f"  SG7B-11 SHA-256         : {frozen_hash}")
    print(f"  Candidate model         : {CANDIDATE_MODEL.name}")
    print(f"  Candidate SHA-256       : {candidate_hash}")
    print(f"  Nominated experiment    : {sg13_manifest.get('experiment')}")
    print("  Candidate identity      : PASS")

    # Independent authorities.
    sg11 = load_module(SG7B11_SOURCE, "pad_stream_sg7b11_for_sg7b14")
    sg10 = load_module(SG7B10_SOURCE, "pad_stream_sg7b10_for_sg7b14")
    base = sg10.load_base_module()
    tf = sg10.tf

    dataset = base.load_dataset()
    sg7a = base.load_sg7a()
    targets = base.build_advective_targets(dataset, sg7a)

    xi = np.asarray(dataset["xi"], dtype=np.float64)
    tD_scale = float(dataset["tD_scale"][0])
    deployment = sg10.load_deployment_database(workspace, tD_scale)
    terminal_days = get_terminal_days(workspace)

    frozen_model = tf.keras.models.load_model(SG7B11_FROZEN_MODEL)
    candidate_model = tf.keras.models.load_model(CANDIDATE_MODEL)

    print("\nAUTHORITATIVE DATABASE")
    print(f"  Held-out profiles       : {len(dataset['X_test']):,}")
    print(f"  xi nodes                : {len(xi)}")
    print(f"  Deployment streamlines  : {len(deployment['X100']):,}")

    # -------------------------------------------------------------------------
    # State / regional accuracy
    # -------------------------------------------------------------------------
    candidate_test = base.evaluate_split(
        candidate_model,
        dataset["X_test"],
        dataset["Y_test"],
        targets["face_test"],
        targets["div_test"],
        xi,
        tD_scale,
    )

    candidate_extra = sg10.additional_preservation_metrics(
        dataset["X_test"],
        candidate_test["truth"],
        candidate_test["prediction"],
    )

    print("\n" + "=" * 78)
    print("HELD-OUT STATE / REGIONAL ACCURACY")
    print("=" * 78)
    print(f"L1                       : {candidate_test['L1']:.6e}")
    print(f"L2                       : {candidate_test['L2']:.6e}")
    print(f"Linf                     : {candidate_test['Linf']:.6e}")
    print(
        f"Prediction range         : "
        f"{candidate_test['minimum_prediction']:.6f} -> "
        f"{candidate_test['maximum_prediction']:.6f}"
    )
    print(f"Mass relative MAE        : {candidate_test['mass_relative_MAE']:.6e}")
    print(f"Injector L1              : {candidate_test['injector_L1']:.6e}")
    print(f"Front L1                 : {candidate_extra['front_L1']:.6e}")
    print(f"Early L1                 : {candidate_extra['early_L1']:.6e}")
    late_key = (
        "late_L1_recomputed"
        if "late_L1_recomputed" in candidate_extra
        else "late_L1"
    )
    print(f"Late L1                  : {candidate_extra[late_key]:.6e}")

    # -------------------------------------------------------------------------
    # Independent canonical physics
    # -------------------------------------------------------------------------
    print("\nBuilding independent SG7A canonical physics reference...")

    canonical_truth = sg11.build_sg7a_canonical_reference(
        base, tf, dataset, sg7a
    )

    frozen_canonical = sg11.canonical_metrics(
        base, tf, frozen_model, dataset, canonical_truth
    )

    candidate_canonical = sg11.canonical_metrics(
        base, tf, candidate_model, dataset, canonical_truth
    )

    # SG7B-11's source code retains the old SG7B-7R E0 constants as an
    # implementation precheck. Those constants are NOT the correct reference
    # for SG7B-14, because SG7B-14 starts from the later front-aware model that
    # SG7B-11 independently accepted and froze.
    #
    # Use the persisted SG7B-11 canonical table as the authoritative reference
    # for the current frozen checkpoint.
    sg7b11_reference = load_sg7b11_front_aware_canonical_reference(
        SG7B11_PHYSICS_TABLE
    )

    # Tight reproduction tolerance: this is the SAME model, SAME independent
    # canonical implementation, and SAME authoritative dataset.
    PRECHECK_REL_TOL = 5.0e-4
    PRECHECK_ABS_TOL_FRAC = 5.0e-5

    precheck_mean = relative_close(
        frozen_canonical["canonical_mean"],
        sg7b11_reference["canonical_mean"],
        PRECHECK_REL_TOL,
    )

    precheck_p90 = relative_close(
        frozen_canonical["canonical_P90"],
        sg7b11_reference["canonical_P90"],
        PRECHECK_REL_TOL,
    )

    precheck_frac = bool(
        abs(
            frozen_canonical["fraction_gt_1"]
            -
            sg7b11_reference["fraction_gt_1"]
        )
        <=
        PRECHECK_ABS_TOL_FRAC
    )

    canonical_precheck_pass = bool(
        precheck_mean
        and
        precheck_p90
        and
        precheck_frac
    )

    print("\n" + "=" * 78)
    print("INDEPENDENT CANONICAL-PHYSICS PRECHECK")
    print("=" * 78)
    print(
        f"Reference checkpoint         : "
        f"{sg7b11_reference['source_label']}"
    )
    print(
        f"SG7A/dataset saturation Linf : "
        f"{canonical_truth['truth_alignment_linf']:.6e}"
    )
    print(
        f"SG7B-11 canonical mean       : "
        f"{frozen_canonical['canonical_mean']:.6e} "
        f"(recorded {sg7b11_reference['canonical_mean']:.6e})"
    )
    print(
        f"SG7B-11 canonical P90        : "
        f"{frozen_canonical['canonical_P90']:.6e} "
        f"(recorded {sg7b11_reference['canonical_P90']:.6e})"
    )
    print(
        f"SG7B-11 fraction > 1         : "
        f"{100.0*frozen_canonical['fraction_gt_1']:.3f}% "
        f"(recorded {100.0*sg7b11_reference['fraction_gt_1']:.3f}%)"
    )
    print(
        f"Mean reproduction            : "
        f"{'PASS' if precheck_mean else 'FAIL'}"
    )
    print(
        f"P90 reproduction             : "
        f"{'PASS' if precheck_p90 else 'FAIL'}"
    )
    print(
        f"Fraction reproduction        : "
        f"{'PASS' if precheck_frac else 'FAIL'}"
    )
    print(
        f"Independent reproduction     : "
        f"{'PASS' if canonical_precheck_pass else 'FAIL'}"
    )

    if not canonical_precheck_pass:
        raise RuntimeError(
            "Independent canonical implementation does not reproduce the "
            "persisted SG7B-11 front-aware frozen canonical metrics. "
            "Do not evaluate the SG7B-13 candidate until this identity "
            "precheck is resolved."
        )

    print("\n" + "=" * 78)
    print("CANDIDATE CANONICAL PHYSICS")
    print("=" * 78)
    print(f"Absolute deltaR MAE      : {candidate_canonical['absolute_deltaR_MAE']:.6e}")
    print(f"Canonical mean           : {candidate_canonical['canonical_mean']:.6e}")
    print(f"Canonical RMS            : {candidate_canonical['canonical_RMS']:.6e}")
    print(f"Canonical P90            : {candidate_canonical['canonical_P90']:.6e}")
    print(f"Canonical P95            : {candidate_canonical['canonical_P95']:.6e}")
    print(f"Canonical P99            : {candidate_canonical['canonical_P99']:.6e}")
    print(f"Fraction > 1             : {100.0*candidate_canonical['fraction_gt_1']:.3f}%")

    # -------------------------------------------------------------------------
    # Deployment, front, shape, TOF-bias
    # -------------------------------------------------------------------------
    deployment_prediction = candidate_model.predict(
        deployment["X100"],
        batch_size=sg10.BATCH_SIZE,
        verbose=0,
    )[:, :, 0]

    front = independent_front_metrics(
        deployment_prediction,
        deployment["truth100"],
    )

    bias = independent_bias_metrics(
        deployment_prediction,
        deployment["truth100"],
        terminal_days,
    )

    front_contract = sg10s_contract["front_improvement_contract"]
    min_fronts = int(front_contract["minimum_recovered_fronts"])
    max_gap = float(front_contract["maximum_conditioned_threshold_gap"])
    max_profile_l1 = float(front_contract["maximum_100d_profile_L1"])

    local_mask = sg11.front_pair_mask(
        deployment["truth100"],
        sg10.FRONT_HIGH,
        sg10.CROSSING_LOW,
    )

    candidate_shape = sg11.local_shape_metrics(
        deployment_prediction,
        deployment["truth100"],
        deployment["xi"],
        local_mask,
        sg10.MONOTONIC_TOL,
    )

    shape_gate_results = []
    for gate in sg10s_contract["shape_preservation_gates"]:
        key = str(gate["gate"])
        value = float(candidate_shape[key])
        limit = float(gate["candidate_limit"])
        shape_gate_results.append({
            "gate": key,
            "value": value,
            "limit": limit,
            "passed": bool(value <= limit),
        })
    shape_pass = all(row["passed"] for row in shape_gate_results)

    print("\n" + "=" * 78)
    print("FRONT / TOF-CONDITIONED DEPLOYMENT VALIDATION")
    print("=" * 78)
    print(
        f"Recovered fronts         : "
        f"{front['recovered_front_count']} / {front['truth_front_count']}"
    )
    print(f"Conditioned front gap    : {front['conditioned_threshold_gap_mean']:.6e}")
    print(f"100d profile L1          : {front['profile_L1_mean']:.6e}")
    print(f"500-1000d mean bias      : {bias['bias_500_1000']:.6e}")
    print(f"1000-2000d mean bias     : {bias['bias_1000_2000']:.6e}")
    print(f">2000d mean bias         : {bias['bias_gt2000']:.6e}")
    print(f"Initial-tail mean bias   : {bias['tail_bias']:.6e}")
    print(
        f"500-1000d material share : "
        f"{100.0*bias['material_share_500_1000']:.2f}%"
    )
    print(
        f"500-1000d abs-bias guard : "
        f"{abs(bias['bias_500_1000']):.6e} <= {MAX_ABS_BIAS_500_1000:.6e}"
    )

    # -------------------------------------------------------------------------
    # Final gates
    # -------------------------------------------------------------------------
    gates = [
        ("Model loads successfully", True, "load", 1.0, 1.0),
        (
            "Predictions finite",
            bool(
                np.all(np.isfinite(candidate_test["prediction"]))
                and np.all(np.isfinite(deployment_prediction))
            ),
            "finite", 1.0, 1.0,
        ),
        (
            "Saturation lower bound respected",
            candidate_test["minimum_prediction"] >= base.S_INITIAL - 1e-7,
            ">=", candidate_test["minimum_prediction"], base.S_INITIAL,
        ),
        (
            "Saturation upper bound respected",
            candidate_test["maximum_prediction"] <= base.S_INJECTED + 1e-7,
            "<=", candidate_test["maximum_prediction"], base.S_INJECTED,
        ),
        ("Held-out L1 < 0.020", candidate_test["L1"] < MAX_L1, "<", candidate_test["L1"], MAX_L1),
        ("Held-out L2 < 0.030", candidate_test["L2"] < MAX_L2, "<", candidate_test["L2"], MAX_L2),
        (
            "Mass relative MAE < 0.030",
            candidate_test["mass_relative_MAE"] < MAX_MASS_RELATIVE_MAE,
            "<", candidate_test["mass_relative_MAE"], MAX_MASS_RELATIVE_MAE,
        ),
        (
            "Canonical mean < 0.500",
            candidate_canonical["canonical_mean"] < MAX_CANONICAL_MEAN,
            "<", candidate_canonical["canonical_mean"], MAX_CANONICAL_MEAN,
        ),
        (
            "Canonical P90 < 1.000",
            candidate_canonical["canonical_P90"] < MAX_CANONICAL_P90,
            "<", candidate_canonical["canonical_P90"], MAX_CANONICAL_P90,
        ),
        (
            "Canonical fraction > 1 < 10%",
            candidate_canonical["fraction_gt_1"] < MAX_CANONICAL_FRAC_GT1,
            "<", candidate_canonical["fraction_gt_1"], MAX_CANONICAL_FRAC_GT1,
        ),
        (
            "Injector-region L1 < 0.015",
            candidate_test["injector_L1"] < MAX_INJECTOR_L1,
            "<", candidate_test["injector_L1"], MAX_INJECTOR_L1,
        ),
        (
            "Front-region L1 < 0.030",
            candidate_extra["front_L1"] < MAX_FRONT_L1,
            "<", candidate_extra["front_L1"], MAX_FRONT_L1,
        ),
        (
            "Early-time L1 < 0.020",
            candidate_extra["early_L1"] < MAX_EARLY_L1,
            "<", candidate_extra["early_L1"], MAX_EARLY_L1,
        ),
        (
            "Late-time L1 < 0.025",
            candidate_extra[late_key] < MAX_LATE_L1,
            "<", candidate_extra[late_key], MAX_LATE_L1,
        ),
        (
            f"Recovered fronts >= {min_fronts}",
            front["recovered_front_count"] >= min_fronts,
            ">=", front["recovered_front_count"], min_fronts,
        ),
        (
            "Conditioned front gap within SG7B-10S contract",
            front["conditioned_threshold_gap_mean"] <= max_gap,
            "<=", front["conditioned_threshold_gap_mean"], max_gap,
        ),
        (
            "100d profile L1 within SG7B-10S contract",
            front["profile_L1_mean"] <= max_profile_l1,
            "<=", front["profile_L1_mean"], max_profile_l1,
        ),
        (
            "SG7A/E0-relative front shape preserved",
            shape_pass,
            "all", 1.0 if shape_pass else 0.0, 1.0,
        ),
        (
            "500-1000d mean bias <= 2.5e-3",
            bias["bias_500_1000"] <= MAX_BIAS_500_1000,
            "<=", bias["bias_500_1000"], MAX_BIAS_500_1000,
        ),
        (
            "500-1000d absolute mean bias <= 2.5e-3",
            abs(bias["bias_500_1000"]) <= MAX_ABS_BIAS_500_1000,
            "<=", abs(bias["bias_500_1000"]), MAX_ABS_BIAS_500_1000,
        ),
        (
            "1000-2000d mean bias <= 4.5e-3",
            bias["bias_1000_2000"] <= MAX_BIAS_1000_2000,
            "<=", bias["bias_1000_2000"], MAX_BIAS_1000_2000,
        ),
        (
            ">2000d mean bias <= 5.0e-3",
            bias["bias_gt2000"] <= MAX_BIAS_GT2000,
            "<=", bias["bias_gt2000"], MAX_BIAS_GT2000,
        ),
        (
            "Initial-tail mean bias <= 5.0e-3",
            bias["tail_bias"] <= MAX_TAIL_BIAS,
            "<=", bias["tail_bias"], MAX_TAIL_BIAS,
        ),
        (
            "500-1000d material-positive share <= 40%",
            bias["material_share_500_1000"] <= MAX_500_1000_MATERIAL_SHARE,
            "<=", bias["material_share_500_1000"], MAX_500_1000_MATERIAL_SHARE,
        ),
    ]

    passed = all(bool(flag) for _, flag, _, _, _ in gates)

    print("\n" + "=" * 78)
    print("V15-SG7B-14 FINAL INDEPENDENT GATES")
    print("=" * 78)
    for description, flag, _, _, _ in gates:
        print(f"[{'PASS' if flag else 'FAIL'}] {description}")
    print("=" * 78)

    # -------------------------------------------------------------------------
    # Save tables / numerical outputs
    # -------------------------------------------------------------------------
    save_csv(GATE_TABLE, [
        {
            "gate": desc,
            "passed": bool(flag),
            "operator": op,
            "value": float(value),
            "threshold": float(limit),
        }
        for desc, flag, op, value, limit in gates
    ])

    save_csv(PHYSICS_TABLE, [
        {
            "model": "SG7B11_frozen_precheck",
            **{
                key: float(frozen_canonical[key])
                for key in [
                    "absolute_deltaR_MAE", "canonical_mean", "canonical_RMS",
                    "canonical_P50", "canonical_P90", "canonical_P95",
                    "canonical_P99", "fraction_gt_1",
                ]
            },
        },
        {
            "model": "SG7B13_candidate",
            **{
                key: float(candidate_canonical[key])
                for key in [
                    "absolute_deltaR_MAE", "canonical_mean", "canonical_RMS",
                    "canonical_P50", "canonical_P90", "canonical_P95",
                    "canonical_P99", "fraction_gt_1",
                ]
            },
        },
    ])

    save_csv(REGIONAL_TABLE, [{
        "L1": candidate_test["L1"],
        "L2": candidate_test["L2"],
        "Linf": candidate_test["Linf"],
        "mass_relative_MAE": candidate_test["mass_relative_MAE"],
        "injector_L1": candidate_test["injector_L1"],
        "front_L1": candidate_extra["front_L1"],
        "early_L1": candidate_extra["early_L1"],
        "late_L1": candidate_extra[late_key],
    }])

    save_csv(BIAS_TABLE, [{
        **bias,
        "absolute_bias_500_1000": abs(bias["bias_500_1000"]),
    }])

    save_csv(SHAPE_TABLE, shape_gate_results)

    np.savez_compressed(
        NUMERICAL_FILE,
        heldout_prediction=np.asarray(candidate_test["prediction"], dtype=np.float32),
        heldout_truth=np.asarray(candidate_test["truth"], dtype=np.float32),
        deployment_candidate100=deployment_prediction.astype(np.float32),
        deployment_truth100=np.asarray(deployment["truth100"], dtype=np.float32),
        terminal_days=terminal_days.astype(np.float64),
        xi=np.asarray(deployment["xi"], dtype=np.float32),
    )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    labels = ["500-1000d", "1000-2000d", ">2000d", "tail"]
    values = [
        bias["bias_500_1000"],
        bias["bias_1000_2000"],
        bias["bias_gt2000"],
        bias["tail_bias"],
    ]
    plt.bar(labels, values)
    plt.axhline(0.0, linestyle="--")
    plt.ylabel("Mean PI-RNN - SG7A bias")
    plt.title("V15-SG7B-14 independent TOF-bias validation")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B14_TOF_Bias.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 5))
    plt.hist(candidate_canonical["scaled"].ravel(), bins=80)
    plt.axvline(1.0, linestyle="--")
    plt.xlabel("SG7A-activity-scaled residual discrepancy")
    plt.ylabel("Samples")
    plt.title("V15-SG7B-14 candidate canonical physics")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B14_Canonical_Distribution.png", dpi=300)
    plt.close()

    # -------------------------------------------------------------------------
    # Freeze decision
    # -------------------------------------------------------------------------
    if passed:
        shutil.copy2(CANDIDATE_MODEL, FROZEN_MODEL)
        frozen_candidate_hash = sha256_file(FROZEN_MODEL)

        status = "TOF_CONDITIONED_PI_RNN_FROZEN"
        recommendation = (
            "The SG7B-13 E3 candidate independently satisfies the complete "
            "SG7B-11 preservation/canonical-physics contract, the SG7B-10S "
            "front-shape contract, the SG7B-12 TOF-bias contract, and the "
            "500-1000 d overshoot guard. The new TOF-conditioned frozen model "
            "may now be redeployed through the unchanged SGSim streamline/grid pathway."
        )
        next_milestone = (
            "V15-SG7C-R3 — TOF-Conditioned Frozen PI-RNN Redeployment on SGSim Streamlines"
        )
    else:
        frozen_candidate_hash = None
        status = "TOF_CONDITIONED_CANDIDATE_VALIDATION_FAILED"
        recommendation = (
            "Do not freeze or redeploy the SG7B-13 candidate. Keep the SG7B-11 "
            "front-aware frozen model authoritative and diagnose the failed "
            "independent preservation, canonical, shape, or TOF-bias gates."
        )
        next_milestone = (
            "V15-SG7B-14R — Independent TOF-Conditioned Candidate Regression Audit"
        )

    manifest = {
        "milestone": "V15-SG7B-14",
        "status": status,
        "candidate_source": str(CANDIDATE_MODEL),
        "candidate_sha256": candidate_hash,
        "nominated_experiment": sg13_manifest.get("experiment"),
        "SG7B11_frozen_model": str(SG7B11_FROZEN_MODEL),
        "SG7B11_frozen_sha256": frozen_hash,
        "SG7B11_overwritten": False,
        "validation_passed": bool(passed),
        "new_frozen_model": str(FROZEN_MODEL) if passed else None,
        "new_frozen_sha256": frozen_candidate_hash,
    }
    save_json(FREEZE_MANIFEST, manifest)

    summary = {
        "milestone": "V15-SG7B-14",
        "status": status,
        "validation_passed": bool(passed),
        "candidate_sha256": candidate_hash,
        "new_frozen_sha256": frozen_candidate_hash,
        "canonical_metrics": {
            "mean": candidate_canonical["canonical_mean"],
            "P90": candidate_canonical["canonical_P90"],
            "fraction_gt_1": candidate_canonical["fraction_gt_1"],
        },
        "front_metrics": front,
        "bias_metrics": bias,
        "shape_preserved": bool(shape_pass),
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }
    save_json(SUMMARY_FILE, summary)

    print("\nSTATUS")
    print(f"  {status}")

    if passed:
        print("\nNEW TOF-CONDITIONED FROZEN MODEL")
        print(f"  {FROZEN_MODEL.name}")
        print("\nSHA-256")
        print(f"  {frozen_candidate_hash}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {GATE_TABLE.name}")
    print(f"  {PHYSICS_TABLE.name}")
    print(f"  {REGIONAL_TABLE.name}")
    print(f"  {BIAS_TABLE.name}")
    print(f"  {SHAPE_TABLE.name}")
    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")
    print("\nFreeze manifest:")
    print(f"  {FREEZE_MANIFEST.name}")
    print("\nDiagnostics:")
    print("  V15SG7B14_TOF_Bias.png")
    print("  V15SG7B14_Canonical_Distribution.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print(
        "V15-SG7B-14 FINAL VALIDATION: "
        + ("PASS" if passed else "FAIL")
    )
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()