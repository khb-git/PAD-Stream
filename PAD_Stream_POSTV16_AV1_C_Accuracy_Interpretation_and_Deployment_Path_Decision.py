#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV1-C"
STATUS_PASS = "AV1C_REPRESENTATION_ACCEPTED_NO_REPAIR_MODEL_DEPLOYMENT_REQUIRES_PHYSICAL_IMPACT_AUDIT"
STATUS_BLOCKED = "AV1C_ACCURACY_INTERPRETATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

B1R1_COMMIT = "cbe7be7f5ca74a63127b990f91cf5b34d7d1e8b3"
B1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_"
    "Representation_Equivalence_Audit.py"
)
B1R1_RUNNER_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"

B1_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_Representation_Equivalence_Audit"
)

B1_SUMMARY = "PAD_Stream_POSTV16_AV1_B1_Summary.json"
B1_CLOSURE = "POSTV16_AV1_B1_Final_Closure.json"
B1_ARRAYS = "POSTV16_AV1_B1_Level1_Level2_Arrays.npz"
B1_DAY = "POSTV16_AV1_B1_Level1_Level2_By_Target_Day.csv"
B1_GATES = "POSTV16_AV1_B1_Final_Gate_Matrix.csv"
B1_MANIFEST = "POSTV16_AV1_B1_Artifact_Manifest.csv"

B1_STATUS = "AV1B1R1_C26_TO_E37A_COMPONENT_MASS_RUNTIME_REPRESENTATION_EQUIVALENCE_AUDITED"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_C_Accuracy_Interpretation_and_Deployment_Path_Decision"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_C_BLOCKED"
)

EXPECTED_SAMPLES = 1449
EXPECTED_NODES = 201
EXPECTED_CVS = 200
EXPECTED_STREAMLINES = 161
EXPECTED_DAYS = np.array(
    [30., 60., 100., 150., 250., 365., 500., 750., 1000.],
    dtype=np.float64,
)

# Numerical-only tolerance for recomputation identity and monotonic comparison.
NUM_TOL = 5.0e-13


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
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
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    e = np.asarray(pred, dtype=np.float64) - np.asarray(truth, dtype=np.float64)
    mse = float(np.mean(e * e))
    return {
        "mse": mse,
        "rmse": float(np.sqrt(mse)),
        "mae": float(np.mean(np.abs(e))),
        "max_abs_error": float(np.max(np.abs(e))),
    }


def percentile_dict(x: np.ndarray, prefix: str) -> dict[str, float]:
    a = np.asarray(x, dtype=np.float64)
    return {
        f"{prefix}_p50": float(np.percentile(a, 50.0)),
        f"{prefix}_p90": float(np.percentile(a, 90.0)),
        f"{prefix}_p95": float(np.percentile(a, 95.0)),
        f"{prefix}_p99": float(np.percentile(a, 99.0)),
        f"{prefix}_max": float(np.max(a)),
    }


def check_manifest(out: Path) -> dict[str, str]:
    rows = read_csv(out / B1_MANIFEST)
    d = {r["file"]: r["sha256"] for r in rows}
    required = [B1_SUMMARY, B1_CLOSURE, B1_ARRAYS, B1_DAY, B1_GATES]
    missing = [name for name in required if name not in d]
    if missing:
        raise GateError(f"B1_manifest_missing_entries:{missing}")
    for name in required:
        p = out / name
        if not p.is_file():
            raise GateError(f"B1_artifact_missing:{name}")
        actual = sha256_file(p)
        if actual != d[name]:
            raise GateError(f"B1_manifest_SHA_mismatch:{name}:{actual}:{d[name]}")
    return d


def self_test() -> None:
    rng = np.random.default_rng(16031)
    truth = rng.uniform(0.2, 0.8, size=(7, 200))
    pred1 = truth + rng.normal(0.0, 0.01, size=truth.shape)
    pred2 = truth + rng.normal(0.0, 0.009, size=truth.shape)
    m1 = metrics(pred1, truth)
    m2 = metrics(pred2, truth)
    if not all(k in m1 for k in ("rmse", "mae", "max_abs_error")):
        raise RuntimeError("self_test_metrics_missing")
    mass_truth = rng.uniform(0.0, 100.0, size=(7, 200))
    mass_pred = mass_truth * 1.01
    true_total = np.sum(mass_truth, axis=1)
    pred_total = np.sum(mass_pred, axis=1)
    rel = np.abs(pred_total - true_total) / np.maximum(np.abs(true_total), 1.0)
    if not np.all(rel > 0.0):
        raise RuntimeError("self_test_mass_relative_error")
    if percentile_dict(rel, "x")["x_p95"] <= 0.0:
        raise RuntimeError("self_test_percentiles")
    print("POSTV16-AV1-C self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("=" * 168)
    print("POSTV16-AV1-C — ACCURACY INTERPRETATION AND DEPLOYMENT-PATH DECISION")
    print("=" * 168)
    print("CONSUMES CERTIFIED B1-R1 OUTPUTS ONLY.")
    print("NO MODEL INFERENCE. NO TRAINING/RETUNING. NO NEW ACCURACY THRESHOLD.")
    print("NO TRANSPORT TIME MARCH. NO GRID MAPBACK. NO FROZEN ARTIFACT MUTATION.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_B1R1_commit",
            parent == B1R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        b1_runner = root / B1R1_RUNNER
        actual_blob = (
            git_blob_sha(b1_runner, root)
            if b1_runner.is_file()
            else "missing"
        )
        gate(
            "B1R1_runner_blob_exact",
            actual_blob == B1R1_RUNNER_BLOB,
            actual_blob,
        )

        stage = "B1R1_artifact_binding"
        b1_out = drive / B1_OUT_REL
        gate("B1R1_output_directory_present", b1_out.is_dir(), str(b1_out))

        manifest = check_manifest(b1_out)
        gate("B1R1_manifest_internal_SHA_closure", True, len(manifest))

        summary = load_json(b1_out / B1_SUMMARY)
        closure = load_json(b1_out / B1_CLOSURE)
        day_existing = read_csv(b1_out / B1_DAY)

        gate("B1R1_status_exact", summary.get("status") == B1_STATUS, summary.get("status"))
        gate("B1R1_closure_status_exact", closure.get("status") == B1_STATUS, closure.get("status"))
        gate("B1R1_all_gates_passed", closure.get("all_gates_passed") is True)
        gate("B1R1_level1_completed", closure.get("level1_completed") is True)
        gate(
            "B1R1_level2_component_mass_projection_completed",
            closure.get("level2_component_mass_projection_completed") is True,
        )
        gate(
            "B1R1_E37A_exact_pressure_mass_coefficients_used",
            closure.get("E37A_exact_pressure_mass_coefficients_used") is True,
        )
        gate("B1R1_saturation_average_not_used", closure.get("saturation_average_used") is False)
        gate("B1R1_training_or_retuning_false", closure.get("training_or_retuning") is False)

        stage = "recompute"
        a = load_npz(b1_out / B1_ARRAYS)

        pred201 = np.asarray(a["C26_pred_201"], dtype=np.float64)
        true201 = np.asarray(a["C17_true_201"], dtype=np.float64)
        pred200 = np.asarray(a["C26_pred_E37A_200"], dtype=np.float64)
        true200 = np.asarray(a["C17_true_E37A_200"], dtype=np.float64)
        pred_mass = np.asarray(a["C26_component_mass_200_kg"], dtype=np.float64)
        true_mass = np.asarray(a["C17_component_mass_200_kg"], dtype=np.float64)
        days = np.asarray(a["target_time_days"], dtype=np.float64)
        streamlines = np.asarray(a["streamline_index"], dtype=np.int64)

        gate("arrays_pred201_shape", pred201.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), pred201.shape)
        gate("arrays_true201_shape", true201.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), true201.shape)
        gate("arrays_pred200_shape", pred200.shape == (EXPECTED_SAMPLES, EXPECTED_CVS), pred200.shape)
        gate("arrays_true200_shape", true200.shape == (EXPECTED_SAMPLES, EXPECTED_CVS), true200.shape)
        gate("arrays_pred_mass_shape", pred_mass.shape == (EXPECTED_SAMPLES, EXPECTED_CVS), pred_mass.shape)
        gate("arrays_true_mass_shape", true_mass.shape == (EXPECTED_SAMPLES, EXPECTED_CVS), true_mass.shape)
        gate("locked_test_streamlines_161", len(np.unique(streamlines)) == EXPECTED_STREAMLINES, len(np.unique(streamlines)))
        gate("target_days_exact", np.array_equal(np.unique(days), EXPECTED_DAYS), np.unique(days).tolist())
        gate("all_arrays_finite", all(np.isfinite(x).all() for x in [pred201, true201, pred200, true200, pred_mass, true_mass]))

        level1 = metrics(pred201, true201)
        level2 = metrics(pred200, true200)

        s1 = summary["level1_native_201_state_metrics"]
        s2 = summary["level2_E37A_200_CV_component_mass_metrics"]

        for key in ("mse", "rmse", "mae", "max_abs_error"):
            gate(
                f"level1_{key}_recomputes_B1R1",
                abs(level1[key] - float(s1[key])) <= NUM_TOL,
                f"{level1[key]} vs {s1[key]}",
            )
            gate(
                f"level2_{key}_recomputes_B1R1",
                abs(level2[key] - float(s2[key])) <= NUM_TOL,
                f"{level2[key]} vs {s2[key]}",
            )

        # Representation question: exact bridge must not amplify the three
        # principal saturation-error measures. This is NOT a deployment-accuracy
        # threshold; it is a monotonic representation-degradation test.
        gate(
            "representation_RMSE_not_amplified",
            level2["rmse"] <= level1["rmse"] + NUM_TOL,
            (level1["rmse"], level2["rmse"]),
        )
        gate(
            "representation_MAE_not_amplified",
            level2["mae"] <= level1["mae"] + NUM_TOL,
            (level1["mae"], level2["mae"]),
        )
        gate(
            "representation_max_abs_not_amplified",
            level2["max_abs_error"] <= level1["max_abs_error"] + NUM_TOL,
            (level1["max_abs_error"], level2["max_abs_error"]),
        )

        rmse_change_pct = 100.0 * (level2["rmse"] - level1["rmse"]) / level1["rmse"]
        mae_change_pct = 100.0 * (level2["mae"] - level1["mae"]) / level1["mae"]
        max_change_pct = 100.0 * (level2["max_abs_error"] - level1["max_abs_error"]) / level1["max_abs_error"]

        stage = "component_mass_interpretation"

        mass_diff = pred_mass - true_mass
        pred_total = np.sum(pred_mass, axis=1)
        true_total = np.sum(true_mass, axis=1)
        inventory_diff = pred_total - true_total

        # Relative inventory error uses a 1 kg denominator floor solely to avoid
        # division by zero for truly empty/near-empty samples; no pass/fail
        # threshold is attached to this diagnostic.
        inventory_abs_rel = np.abs(inventory_diff) / np.maximum(np.abs(true_total), 1.0)
        inventory_signed_rel = inventory_diff / np.maximum(np.abs(true_total), 1.0)

        local_mass_L1_rel = (
            np.sum(np.abs(mass_diff), axis=1)
            / np.maximum(np.sum(np.abs(true_mass), axis=1), 1.0)
        )

        mass_summary = {
            "inventory_bias_kg_mean": float(np.mean(inventory_diff)),
            "inventory_error_kg_mae": float(np.mean(np.abs(inventory_diff))),
            "inventory_error_kg_rmse": float(np.sqrt(np.mean(inventory_diff ** 2))),
            "inventory_abs_relative_mean": float(np.mean(inventory_abs_rel)),
            "inventory_signed_relative_mean": float(np.mean(inventory_signed_rel)),
            "local_mass_L1_relative_mean": float(np.mean(local_mass_L1_rel)),
            **percentile_dict(inventory_abs_rel, "inventory_abs_relative"),
            **percentile_dict(local_mass_L1_rel, "local_mass_L1_relative"),
        }

        # Error localization with no fitted threshold: define the true front as
        # the CV adjacent to the largest absolute true-state gradient.
        true_grad = np.abs(np.diff(true200, axis=1))
        front_index = np.argmax(true_grad, axis=1)
        e200 = np.abs(pred200 - true200)

        front_err = np.empty(EXPECTED_SAMPLES, dtype=np.float64)
        off_front_sq_sum = 0.0
        off_front_n = 0

        for n in range(EXPECTED_SAMPLES):
            j = int(front_index[n])
            lo = max(0, j - 2)
            hi = min(EXPECTED_CVS, j + 3)
            front_err[n] = float(np.max(e200[n, lo:hi]))
            mask = np.ones(EXPECTED_CVS, dtype=bool)
            mask[lo:hi] = False
            off = e200[n, mask]
            off_front_sq_sum += float(np.sum(off * off))
            off_front_n += int(off.size)

        front_summary = {
            "front_definition": "argmax absolute true E37A-200 saturation gradient; diagnostic window ±2 CVs",
            "front_window_max_abs_mean": float(np.mean(front_err)),
            "front_window_max_abs_p95": float(np.percentile(front_err, 95.0)),
            "front_window_max_abs_max": float(np.max(front_err)),
            "off_front_rmse": float(np.sqrt(off_front_sq_sum / max(off_front_n, 1))),
        }

        # By-day diagnostics including component mass.
        day_rows = []
        for day in EXPECTED_DAYS:
            m = np.isclose(days, day, rtol=0.0, atol=1.0e-12)
            l1d = metrics(pred201[m], true201[m])
            l2d = metrics(pred200[m], true200[m])

            mdiff = inventory_diff[m]
            mtrue = true_total[m]
            irel = np.abs(mdiff) / np.maximum(np.abs(mtrue), 1.0)
            lrel = local_mass_L1_rel[m]

            row = {
                "target_day": float(day),
                "samples": int(np.sum(m)),
                "level1_rmse": l1d["rmse"],
                "level1_mae": l1d["mae"],
                "level1_max_abs": l1d["max_abs_error"],
                "level2_rmse": l2d["rmse"],
                "level2_mae": l2d["mae"],
                "level2_max_abs": l2d["max_abs_error"],
                "level2_minus_level1_rmse_pct": (
                    100.0 * (l2d["rmse"] - l1d["rmse"]) / l1d["rmse"]
                    if l1d["rmse"] > 0.0 else 0.0
                ),
                "inventory_bias_kg_mean": float(np.mean(mdiff)),
                "inventory_error_kg_mae": float(np.mean(np.abs(mdiff))),
                "inventory_abs_relative_mean": float(np.mean(irel)),
                "inventory_abs_relative_p95": float(np.percentile(irel, 95.0)),
                "local_mass_L1_relative_mean": float(np.mean(lrel)),
                "local_mass_L1_relative_p95": float(np.percentile(lrel, 95.0)),
            }
            day_rows.append(row)

        # Cross-check B1's by-day saturation table, not its mass diagnostics.
        gate("B1R1_by_day_row_count_9", len(day_existing) == 9, len(day_existing))
        existing_by_day = {float(r["target_day"]): r for r in day_existing}
        for row in day_rows:
            old = existing_by_day[row["target_day"]]
            gate(
                f"day_{int(row['target_day'])}_level1_rmse_recomputes",
                abs(row["level1_rmse"] - float(old["level1_201_rmse"])) <= NUM_TOL,
            )
            gate(
                f"day_{int(row['target_day'])}_level2_rmse_recomputes",
                abs(row["level2_rmse"] - float(old["level2_200_rmse"])) <= NUM_TOL,
            )

        stage = "decision"

        # These are intentionally different decisions.
        representation_repair_required = False
        model_retraining_authorized = False
        final_model_deployment_accepted = False

        gate("representation_repair_not_required", not representation_repair_required)
        gate("no_retraining_or_retuning_authorized", not model_retraining_authorized)
        gate("no_retroactive_accuracy_threshold_selected", True)
        gate("final_model_deployment_not_claimed_from_B1_alone", not final_model_deployment_accepted)
        gate("no_model_inference_executed_in_AV1C", True)
        gate("no_training_or_retuning_executed_in_AV1C", True)
        gate("no_transport_time_march_executed_in_AV1C", True)
        gate("no_grid_mapback_executed_in_AV1C", True)
        gate("no_frozen_artifact_modified", True)

        decision = {
            "representation_decision": "ACCEPTED_NO_REPAIR_REQUIRED",
            "basis": [
                "B1-R1 exact component-mass conservation passed",
                "B1-R1 exact mass inversion closure passed",
                "Level-2 RMSE did not exceed Level-1 RMSE",
                "Level-2 MAE did not exceed Level-1 MAE",
                "Level-2 max absolute saturation error did not exceed Level-1 max absolute error",
            ],
            "model_accuracy_decision": "NOT_YET_FINAL_DEPLOYMENT_ACCEPTED",
            "why_not_final": (
                "No prospective application-level accuracy threshold existed before observing "
                "the locked-test result. AV1-C therefore does not create a favorable threshold "
                "retroactively. The next decision must be based on physical runtime impact."
            ),
            "representation_repair_required": False,
            "retraining_or_retuning_authorized": False,
            "next": (
                "POSTV16-AV1-D — physical-impact deployment audit: propagate frozen C26 and C17 "
                "runtime states through the conservative grid/mapback and compare plume/inventory/"
                "producer-relevant physical outputs without retraining."
            ),
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "repository_head": head,
            "repository_parent": parent,
            "B1R1_output_directory": str(b1_out),
            "locked_test_samples": EXPECTED_SAMPLES,
            "locked_test_streamlines": EXPECTED_STREAMLINES,
            "level1_metrics": level1,
            "level2_metrics": level2,
            "level2_minus_level1_percent": {
                "rmse": rmse_change_pct,
                "mae": mae_change_pct,
                "max_abs_error": max_change_pct,
            },
            "component_mass_diagnostics": mass_summary,
            "front_localization_diagnostics": front_summary,
            "decision": decision,
            "new_accuracy_acceptance_threshold_selected": False,
            "model_inference_executed": False,
            "training_or_retuning_executed": False,
            "transport_time_march_executed": False,
            "grid_mapback_executed": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV1_C_Summary.json": json_bytes(summary_out),
            "POSTV16_AV1_C_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV1_C_By_Target_Day_Diagnostics.csv": csv_bytes(day_rows),
            "POSTV16_AV1_C_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_C_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"POSTV16_AV1_C_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 168)
        print("POSTV16-AV1-C: PASS")
        print("=" * 168)
        print(f"{'Status':86}: {STATUS_PASS}")
        print(
            f"{'Level 1 RMSE / MAE / max abs':86}: "
            f"{level1['rmse']:.12e} / {level1['mae']:.12e} / {level1['max_abs_error']:.12e}"
        )
        print(
            f"{'Level 2 RMSE / MAE / max abs':86}: "
            f"{level2['rmse']:.12e} / {level2['mae']:.12e} / {level2['max_abs_error']:.12e}"
        )
        print(
            f"{'Level2-Level1 change RMSE / MAE / max abs (%)':86}: "
            f"{rmse_change_pct:.6f} / {mae_change_pct:.6f} / {max_change_pct:.6f}"
        )
        print(
            f"{'Inventory error MAE / RMSE (kg)':86}: "
            f"{mass_summary['inventory_error_kg_mae']:.12e} / "
            f"{mass_summary['inventory_error_kg_rmse']:.12e}"
        )
        print(
            f"{'Inventory absolute relative mean / p95 / max':86}: "
            f"{mass_summary['inventory_abs_relative_mean']:.12e} / "
            f"{mass_summary['inventory_abs_relative_p95']:.12e} / "
            f"{mass_summary['inventory_abs_relative_max']:.12e}"
        )
        print(
            f"{'Local component-mass L1 relative mean / p95 / max':86}: "
            f"{mass_summary['local_mass_L1_relative_mean']:.12e} / "
            f"{mass_summary['local_mass_L1_relative_p95']:.12e} / "
            f"{mass_summary['local_mass_L1_relative_max']:.12e}"
        )
        print(f"{'Representation decision':86}: ACCEPTED_NO_REPAIR_REQUIRED")
        print(f"{'Representation repair required':86}: False")
        print(f"{'Retraining / retuning authorized':86}: False")
        print(f"{'Final model deployment accepted from B1 alone':86}: False")
        print(f"{'New retroactive accuracy threshold selected':86}: False")
        print(
            f"{'NEXT':86}: POSTV16-AV1-D — physical-impact deployment audit"
        )
        print("=" * 168)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "training_or_retuning": False,
            "frozen_artifact_mutation": False,
            "next_action": "Audit only the failed AV1-C gate(s); do not advance to AV1-D.",
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_C_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_C_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-C: BLOCKED")
        print("=" * 168)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
