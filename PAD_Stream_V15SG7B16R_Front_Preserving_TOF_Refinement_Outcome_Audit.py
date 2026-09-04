from __future__ import annotations

from pathlib import Path
import csv
import json

import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

SG7B16_SUMMARY = ROOT / "output" / "V15_SG7B16" / "PAD_Stream_V15SG7B16_Summary.json"
SG7B16_EXPERIMENT_METRICS = ROOT / "output" / "V15_SG7B16" / "V15SG7B16_Experiment_Metrics.csv"
SG7B16_EPOCH_METRICS = ROOT / "output" / "V15_SG7B16" / "V15SG7B16_Epoch_Metrics.csv"
SG7B16_FINAL_GATES = ROOT / "output" / "V15_SG7B16" / "V15SG7B16_Final_Gate_Matrix.csv"
SG7B16_SHAPE_GATES = ROOT / "output" / "V15_SG7B16" / "V15SG7B16_Front_Shape_Gates.csv"
SG7B15R_CONTRACT = ROOT / "output" / "V15_SG7B15R" / "V15SG7B15R_Front_Preserving_TOF_Refinement_Contract.json"

OUTPUT_DIR = ROOT / "output" / "V15_SG7B16R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAJECTORY_TABLE = OUTPUT_DIR / "V15SG7B16R_Epoch_Trajectory_Audit.csv"
PARETO_TABLE = OUTPUT_DIR / "V15SG7B16R_Pareto_Frontier.csv"
FIRST_FAILURE_TABLE = OUTPUT_DIR / "V15SG7B16R_First_Failure_By_Experiment.csv"
GATE_FAILURE_COUNTS = OUTPUT_DIR / "V15SG7B16R_Gate_Failure_Counts.csv"
BEST_CHECKPOINT_TABLE = OUTPUT_DIR / "V15SG7B16R_Best_Compromise_Checkpoints.csv"
SUMMARY_FILE = OUTPUT_DIR / "PAD_Stream_V15SG7B16R_Summary.json"


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def f(row, key, default=np.nan):
    try:
        return float(row.get(key, default))
    except Exception:
        return default


def b(row, key, default=False):
    return str(row.get(key, default)).strip().lower() in {"true", "1", "yes", "pass"}


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-16R")
    print("Front-Preserving TOF Refinement Outcome Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO FRONT, PHYSICS, TOF-BIAS, OR SG7E GATE WILL BE RELAXED.")

    for p in [
        SG7B16_SUMMARY, SG7B16_EXPERIMENT_METRICS, SG7B16_EPOCH_METRICS,
        SG7B16_FINAL_GATES, SG7B16_SHAPE_GATES, SG7B15R_CONTRACT
    ]:
        if not p.exists():
            raise FileNotFoundError(f"Missing SG7B-16R prerequisite:\n{p}")

    summary16 = load_json(SG7B16_SUMMARY)
    contract = load_json(SG7B15R_CONTRACT)

    if summary16.get("status") != "NO_SG7B16_CANDIDATE_PASSES_COMPLETE_CONTRACT":
        raise RuntimeError(
            "SG7B-16R requires SG7B-16 status "
            "NO_SG7B16_CANDIDATE_PASSES_COMPLETE_CONTRACT."
        )

    epoch_metrics = load_csv(SG7B16_EPOCH_METRICS)
    final_gates = load_csv(SG7B16_FINAL_GATES)
    shape_gates = load_csv(SG7B16_SHAPE_GATES)

    front_contract = contract["authoritative_front_improvement_contract"]
    guards = contract["new_front_guards"]

    gap_limit = float(front_contract["maximum_conditioned_threshold_gap"])
    profile_limit = float(front_contract["maximum_100d_profile_L1"])
    anchor_limit = float(guards["maximum_front_anchor_MAE"])
    xi_mean_limit = float(guards["maximum_mean_frozen_front_xi_shift"])
    xi_p90_limit = float(guards["maximum_P90_frozen_front_xi_shift"])

    bias_limits = {
        "bias_500_1000": 2.5e-3,
        "bias_1000_2000": 4.5e-3,
        "bias_gt2000": 5.0e-3,
        "tail_bias": 5.0e-3,
        "material_share": 0.40,
    }

    print("\nAUTHORITATIVE AUDIT LIMITS")
    print(f"  Conditioned gap         : <= {gap_limit:.17e}")
    print(f"  100d profile L1         : <= {profile_limit:.17e}")
    print(f"  Front anchor MAE        : <= {anchor_limit:.6e}")
    print(f"  Front xi mean shift     : <= {xi_mean_limit:.6e}")
    print(f"  Front xi P90 shift      : <= {xi_p90_limit:.6e}")

    trajectory_rows = []
    first_failure_rows = []
    best_compromise_rows = []

    experiments = sorted({str(row["experiment"]) for row in epoch_metrics})

    for exp in experiments:
        rows = [row for row in epoch_metrics if str(row["experiment"]) == exp]
        rows.sort(key=lambda row: f(row, "epoch"))

        first_front_regression_epoch = None
        first_bias_success_epoch = None
        first_shape_failure_epoch = None
        first_anchor_failure_epoch = None
        first_xi_failure_epoch = None
        best_distance = np.inf
        best_row = None

        for row in rows:
            epoch = int(f(row, "epoch"))
            gap = f(row, "conditioned_gap")
            anchor = f(row, "front_anchor_MAE")
            xi_mean = f(row, "front_xi_shift_mean")
            xi_p90 = f(row, "front_xi_shift_P90")
            b500 = f(row, "bias_500_1000")
            b1000 = f(row, "bias_1000_2000")
            b2000 = f(row, "bias_gt2000")
            tail = f(row, "tail_bias")
            share = f(row, "material_share")
            shape_pass = bool(round(f(row, "front_shape_pass", 0.0)))

            front_core_pass = (
                gap <= gap_limit
                and anchor <= anchor_limit
                and xi_mean <= xi_mean_limit
                and xi_p90 <= xi_p90_limit
                and shape_pass
            )

            bias_pass = (
                b500 <= bias_limits["bias_500_1000"]
                and b1000 <= bias_limits["bias_1000_2000"]
                and b2000 <= bias_limits["bias_gt2000"]
                and tail <= bias_limits["tail_bias"]
                and share <= bias_limits["material_share"]
            )

            if first_front_regression_epoch is None and not front_core_pass:
                first_front_regression_epoch = epoch
            if first_bias_success_epoch is None and bias_pass:
                first_bias_success_epoch = epoch
            if first_shape_failure_epoch is None and not shape_pass:
                first_shape_failure_epoch = epoch
            if first_anchor_failure_epoch is None and anchor > anchor_limit:
                first_anchor_failure_epoch = epoch
            if first_xi_failure_epoch is None and xi_p90 > xi_p90_limit:
                first_xi_failure_epoch = epoch

            ratios = np.array([
                gap / gap_limit,
                anchor / anchor_limit,
                xi_p90 / xi_p90_limit,
                abs(b500) / bias_limits["bias_500_1000"],
                abs(b1000) / bias_limits["bias_1000_2000"],
                abs(b2000) / bias_limits["bias_gt2000"],
                abs(tail) / bias_limits["tail_bias"],
                share / bias_limits["material_share"],
            ], dtype=float)
            excess = np.maximum(ratios - 1.0, 0.0)
            distance = float(np.sqrt(np.sum(excess**2)))
            if not shape_pass:
                distance += 1.0

            if distance < best_distance:
                best_distance = distance
                best_row = dict(row)

            trajectory_rows.append({
                "experiment": exp,
                "epoch": epoch,
                "conditioned_gap": gap,
                "gap_pass": gap <= gap_limit,
                "front_anchor_MAE": anchor,
                "anchor_pass": anchor <= anchor_limit,
                "front_xi_shift_mean": xi_mean,
                "xi_mean_pass": xi_mean <= xi_mean_limit,
                "front_xi_shift_P90": xi_p90,
                "xi_P90_pass": xi_p90 <= xi_p90_limit,
                "front_shape_pass": shape_pass,
                "bias_500_1000": b500,
                "bias_500_pass": b500 <= bias_limits["bias_500_1000"],
                "bias_1000_2000": b1000,
                "bias_1000_pass": b1000 <= bias_limits["bias_1000_2000"],
                "bias_gt2000": b2000,
                "bias_2000_pass": b2000 <= bias_limits["bias_gt2000"],
                "tail_bias": tail,
                "tail_pass": tail <= bias_limits["tail_bias"],
                "material_share": share,
                "material_share_pass": share <= bias_limits["material_share"],
                "front_core_pass": front_core_pass,
                "bias_contract_pass": bias_pass,
                "normalized_feasible_distance": distance,
            })

        first_failure_rows.append({
            "experiment": exp,
            "first_front_regression_epoch": first_front_regression_epoch,
            "first_shape_failure_epoch": first_shape_failure_epoch,
            "first_anchor_failure_epoch": first_anchor_failure_epoch,
            "first_xi_P90_failure_epoch": first_xi_failure_epoch,
            "first_bias_contract_pass_epoch": first_bias_success_epoch,
        })

        if best_row is not None:
            best_compromise_rows.append({
                "experiment": exp,
                "epoch": int(f(best_row, "epoch")),
                "normalized_feasible_distance": best_distance,
                "conditioned_gap": f(best_row, "conditioned_gap"),
                "front_anchor_MAE": f(best_row, "front_anchor_MAE"),
                "front_xi_shift_P90": f(best_row, "front_xi_shift_P90"),
                "front_shape_pass": bool(round(f(best_row, "front_shape_pass", 0.0))),
                "bias_500_1000": f(best_row, "bias_500_1000"),
                "bias_1000_2000": f(best_row, "bias_1000_2000"),
                "bias_gt2000": f(best_row, "bias_gt2000"),
                "tail_bias": f(best_row, "tail_bias"),
                "material_share": f(best_row, "material_share"),
            })

    save_csv(TRAJECTORY_TABLE, trajectory_rows)
    save_csv(FIRST_FAILURE_TABLE, first_failure_rows)
    save_csv(BEST_CHECKPOINT_TABLE, best_compromise_rows)

    points = []
    for row in trajectory_rows:
        front_cost = (
            row["conditioned_gap"] / gap_limit
            + row["front_anchor_MAE"] / anchor_limit
            + row["front_xi_shift_P90"] / xi_p90_limit
            + (0.0 if row["front_shape_pass"] else 1.0)
        )
        bias_cost = (
            abs(row["bias_500_1000"]) / bias_limits["bias_500_1000"]
            + abs(row["bias_1000_2000"]) / bias_limits["bias_1000_2000"]
            + abs(row["bias_gt2000"]) / bias_limits["bias_gt2000"]
            + abs(row["tail_bias"]) / bias_limits["tail_bias"]
            + row["material_share"] / bias_limits["material_share"]
        )
        points.append({**row, "front_cost": float(front_cost), "bias_cost": float(bias_cost)})

    pareto = []
    for i, p in enumerate(points):
        dominated = False
        for j, q in enumerate(points):
            if i == j:
                continue
            no_worse = q["front_cost"] <= p["front_cost"] and q["bias_cost"] <= p["bias_cost"]
            strictly_better = q["front_cost"] < p["front_cost"] or q["bias_cost"] < p["bias_cost"]
            if no_worse and strictly_better:
                dominated = True
                break
        if not dominated:
            pareto.append(p)

    pareto.sort(key=lambda row: (row["front_cost"], row["bias_cost"]))
    save_csv(PARETO_TABLE, pareto)

    failure_counts = {}
    for row in final_gates:
        if b(row, "passed"):
            continue
        gate = str(row["gate"])
        failure_counts[gate] = failure_counts.get(gate, 0) + 1

    shape_failure_counts = {}
    for row in shape_gates:
        if b(row, "passed"):
            continue
        gate = str(row["gate"])
        shape_failure_counts[gate] = shape_failure_counts.get(gate, 0) + 1

    gate_failure_rows = []
    for gate, count in sorted(failure_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        gate_failure_rows.append({"gate": gate, "failure_count": count, "source": "final_gate_matrix"})
    for gate, count in sorted(shape_failure_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        gate_failure_rows.append({"gate": gate, "failure_count": count, "source": "front_shape_matrix"})
    save_csv(GATE_FAILURE_COUNTS, gate_failure_rows)

    any_bias_success = any(row["bias_contract_pass"] for row in trajectory_rows)
    any_front_success = any(row["front_core_pass"] for row in trajectory_rows)
    any_joint_success = any(
        row["front_core_pass"] and row["bias_contract_pass"]
        for row in trajectory_rows
    )

    min_b500 = min(row["bias_500_1000"] for row in trajectory_rows)
    min_b1000 = min(row["bias_1000_2000"] for row in trajectory_rows)
    min_b2000 = min(row["bias_gt2000"] for row in trajectory_rows)
    min_tail = min(row["tail_bias"] for row in trajectory_rows)
    best_gap = min(row["conditioned_gap"] for row in trajectory_rows)
    best_anchor = min(row["front_anchor_MAE"] for row in trajectory_rows)
    best_xip90 = min(row["front_xi_shift_P90"] for row in trajectory_rows)

    if not any_bias_success and any_front_success:
        diagnosis = "TOF_BIAS_NOT_REACHABLE_UNDER_FRONT_PRESERVATION"
        next_milestone = "V15-SG7C-R3A — Deployment TOF-Coordinate / Model-Transfer Audit"
        recommendation = (
            "Front-preserving states exist, but no epoch reaches the complete TOF-bias contract. "
            "Stop further weight tuning and audit the SGSim deployment TOF coordinate, "
            "nondimensionalization, and canonical-to-streamline model transfer."
        )
    elif any_bias_success and not any_front_success:
        diagnosis = "FRONT_PRESERVATION_NOT_REACHABLE_DURING_BIAS_CORRECTION"
        next_milestone = "V15-SG7B-17D — Hard Front-Constrained Refinement Design"
        recommendation = (
            "Bias-valid states exist, but no front-valid state exists under the current soft constraints. "
            "Use a hard front-constrained strategy rather than another loss-weight sweep."
        )
    elif not any_bias_success and not any_front_success:
        diagnosis = "COUPLED_DEPLOYMENT_TRANSFER_MISMATCH"
        next_milestone = "V15-SG7C-R3A — Deployment TOF-Coordinate / Model-Transfer Audit"
        recommendation = (
            "Neither the complete front contract nor the complete TOF-bias contract is reached. "
            "Further PI-RNN loss tuning is unlikely to resolve the issue; audit deployment conditioning first."
        )
    elif not any_joint_success:
        diagnosis = "DISJOINT_FRONT_AND_BIAS_FEASIBLE_REGIONS"
        next_milestone = "V15-SG7C-R3A — Deployment TOF-Coordinate / Model-Transfer Audit"
        recommendation = (
            "Front-valid and bias-valid states occur on disjoint parts of the trajectory. "
            "Audit the SGSim TOF-conditioning and model-transfer mapping before further retraining."
        )
    else:
        diagnosis = "RECORDED_CHECKPOINT_NEAR_FEASIBLE"
        next_milestone = "V15-SG7B-16B — Checkpoint-Level Independent Candidate Recovery"
        recommendation = (
            "At least one recorded epoch approaches the joint feasible region. "
            "Recover and independently validate that checkpoint before redesign."
        )

    print("\n" + "=" * 78)
    print("SG7B-16 TRAJECTORY FINDINGS")
    print("=" * 78)
    print(f"  Any front-contract epoch : {any_front_success}")
    print(f"  Any bias-contract epoch  : {any_bias_success}")
    print(f"  Any joint-contract epoch : {any_joint_success}")
    print(f"  Best conditioned gap     : {best_gap:.6e}")
    print(f"  Best front-anchor MAE    : {best_anchor:.6e}")
    print(f"  Best xi P90 shift        : {best_xip90:.6e}")
    print(f"  Minimum 500-1000d bias   : {min_b500:.6e}")
    print(f"  Minimum 1000-2000d bias  : {min_b1000:.6e}")
    print(f"  Minimum >2000d bias      : {min_b2000:.6e}")
    print(f"  Minimum tail bias        : {min_tail:.6e}")

    print("\nFIRST FAILURE / SUCCESS BY EXPERIMENT")
    for row in first_failure_rows:
        print(
            f"  {row['experiment']} | "
            f"frontFail={row['first_front_regression_epoch']} | "
            f"shapeFail={row['first_shape_failure_epoch']} | "
            f"anchorFail={row['first_anchor_failure_epoch']} | "
            f"xiFail={row['first_xi_P90_failure_epoch']} | "
            f"biasPass={row['first_bias_contract_pass_epoch']}"
        )

    print("\nPARETO FRONTIER")
    for row in pareto[:12]:
        print(
            f"  {row['experiment']} epoch={row['epoch']:>3d} | "
            f"frontCost={row['front_cost']:.3f} | "
            f"biasCost={row['bias_cost']:.3f} | "
            f"gap={row['conditioned_gap']:.3e} | "
            f"B500={row['bias_500_1000']:.3e}"
        )

    plt.figure(figsize=(9, 6))
    for exp in experiments:
        rows = [r for r in trajectory_rows if r["experiment"] == exp]
        plt.plot(
            [r["bias_500_1000"] for r in rows],
            [r["conditioned_gap"] for r in rows],
            marker="o",
            label=exp,
        )
    plt.axvline(bias_limits["bias_500_1000"], linestyle="--")
    plt.axhline(gap_limit, linestyle="--")
    plt.xlabel("500-1000 d mean bias")
    plt.ylabel("Conditioned front gap")
    plt.title("V15-SG7B-16R Bias vs Front-Gap Trajectories")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B16R_Bias_vs_FrontGap.png", dpi=300)
    plt.close()

    plt.figure(figsize=(9, 6))
    for exp in experiments:
        rows = [r for r in trajectory_rows if r["experiment"] == exp]
        plt.plot(
            [r["bias_500_1000"] for r in rows],
            [r["front_xi_shift_P90"] for r in rows],
            marker="o",
            label=exp,
        )
    plt.axvline(bias_limits["bias_500_1000"], linestyle="--")
    plt.axhline(xi_p90_limit, linestyle="--")
    plt.xlabel("500-1000 d mean bias")
    plt.ylabel("P90 frozen-front xi shift")
    plt.title("V15-SG7B-16R Bias vs Frozen-Front Displacement")
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B16R_Bias_vs_FrontXiShift.png", dpi=300)
    plt.close()

    plt.figure(figsize=(8, 6))
    plt.scatter(
        [r["front_cost"] for r in points],
        [r["bias_cost"] for r in points],
    )
    if pareto:
        plt.plot(
            [r["front_cost"] for r in pareto],
            [r["bias_cost"] for r in pareto],
            marker="o",
        )
    plt.xlabel("Normalized front-preservation cost")
    plt.ylabel("Normalized TOF-bias cost")
    plt.title("V15-SG7B-16R Pareto Audit")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "V15SG7B16R_Pareto_Frontier.png", dpi=300)
    plt.close()

    summary = {
        "milestone": "V15-SG7B-16R",
        "status": "FRONT_PRESERVING_TOF_OUTCOME_AUDIT_COMPLETE",
        "incoming_status": summary16.get("status"),
        "diagnosis": diagnosis,
        "any_front_contract_epoch": bool(any_front_success),
        "any_bias_contract_epoch": bool(any_bias_success),
        "any_joint_contract_epoch": bool(any_joint_success),
        "best_observed": {
            "conditioned_gap": best_gap,
            "front_anchor_MAE": best_anchor,
            "front_xi_shift_P90": best_xip90,
            "bias_500_1000": min_b500,
            "bias_1000_2000": min_b1000,
            "bias_gt2000": min_b2000,
            "tail_bias": min_tail,
        },
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }
    save_json(SUMMARY_FILE, summary)

    print("\n" + "=" * 78)
    print("V15-SG7B-16R DIAGNOSTIC VALIDATION")
    print("=" * 78)
    print("[PASS] SG7B-16 no-candidate status reproduced")
    print("[PASS] Epoch histories loaded")
    print("[PASS] Exact SG7B-15R front guards loaded")
    print("[PASS] Epoch-level front/bias trajectories reconstructed")
    print("[PASS] Pareto frontier computed")
    print("[PASS] First-failure timing established")
    print("[PASS] Final gate-failure counts generated")
    print("[PASS] Diagnostic classification established")
    print("=" * 78)

    print("\nSTATUS")
    print("  FRONT_PRESERVING_TOF_OUTCOME_AUDIT_COMPLETE")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nTables:")
    print(f"  {TRAJECTORY_TABLE.name}")
    print(f"  {PARETO_TABLE.name}")
    print(f"  {FIRST_FAILURE_TABLE.name}")
    print(f"  {GATE_FAILURE_COUNTS.name}")
    print(f"  {BEST_CHECKPOINT_TABLE.name}")
    print("\nDiagnostics:")
    print("  V15SG7B16R_Bias_vs_FrontGap.png")
    print("  V15SG7B16R_Bias_vs_FrontXiShift.png")
    print("  V15SG7B16R_Pareto_Frontier.png")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7B-16R AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
