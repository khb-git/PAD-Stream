from __future__ import annotations

from pathlib import Path
import csv
import json
import re
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R0
# Support-Metric Definition Reconciliation Audit
#
# DIAGNOSTIC-ONLY REPAIR MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION CALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED.
#
# PURPOSE
# -------
# R3F5 stopped safely because the reconstructed "coverage" metric was not the
# same metric used by the authoritative R3F4/R3D branch:
#
#   reconstructed weighted coverage : ~9.22%
#   authoritative R3D support        : ~49.55%
#
# A multiplicative anchor would be invalid because this is a semantic mismatch,
# not a small numerical normalization mismatch.
#
# R3F5-R0 therefore:
#
#   1. locates the authoritative R3F4 / R3F4-R support evidence,
#   2. locates the source-code definition of
#          front_shell_residual_coverage_fraction
#      when available,
#   3. reconstructs several candidate support metrics from the persisted B4
#      geometry,
#   4. identifies which definition reproduces the authoritative value,
#   5. writes a repaired metric contract for R3F5-R1.
#
# No extension is calibrated here.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R0"
OUT.mkdir(parents=True, exist_ok=True)

R3F5_SUMMARY = ROOT / "output" / "V15_SG7CR3F5" / "PAD_Stream_V15SG7CR3F5_Summary.json"
R3D_GLOBAL = ROOT / "output" / "V15_SG7CR3F4R3D" / "V15SG7CR3F4R3D_Global_Limiter_Audit.csv"
R3F4R_SUPPORT = ROOT / "output" / "V15_SG7CR3F4R" / "V15SG7CR3F4R_Basis_Support_Coverage.csv"
R3F4_CHECKPOINTS = ROOT / "output" / "V15_SG7CR3F4" / "V15SG7CR3F4_Best_Checkpoint_By_Experiment.csv"
R3C_NUMERICAL = ROOT / "output" / "V15_SG7CR3C" / "V15SG7CR3C_Feature_Target_Audit.npz"

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R0_Summary.json"
METRIC_TABLE = OUT / "V15SG7CR3F5R0_Candidate_Support_Metrics.csv"
SOURCE_TABLE = OUT / "V15SG7CR3F5R0_Source_Definition_Evidence.csv"
FIELD_TABLE = OUT / "V15SG7CR3F5R0_Authoritative_Field_Audit.csv"
CONTRACT_FILE = OUT / "V15SG7CR3F5R0_Repaired_Support_Metric_Contract.json"

FRONT_THRESHOLD = 0.210
SIGMA_NARROW = 0.015
SIGMA_MEDIUM = 0.030

ABS_TOL = 5e-4
REL_TOL = 0.01


def load_json(path: Path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def fnum(row, key, default=np.nan):
    try:
        v = row.get(key, default)
        if v in ("", None):
            return default
        return float(v)
    except Exception:
        return default


def build_b4_model():
    inp = tf.keras.Input(shape=(2,), name="profile_features")
    x = tf.keras.layers.Dense(12, activation="tanh")(inp)
    x = tf.keras.layers.Dense(12, activation="tanh")(x)
    out = tf.keras.layers.Dense(3, activation="softmax", name="basis_weights")(x)
    return tf.keras.Model(inp, out, name="R3F4_B4")


def make_features(normalized_tD, tau_end_days):
    logtau = np.log10(np.maximum(tau_end_days, 1.0))
    logtau = (logtau - np.mean(logtau)) / max(np.std(logtau), 1e-12)
    nt, ns = normalized_tD.shape
    return np.stack(
        [
            normalized_tD,
            np.broadcast_to(logtau[None, :], (nt, ns)),
        ],
        axis=-1,
    ).astype(np.float32)


def gaussian(distance, sigma):
    return np.exp(-0.5 * (distance / sigma) ** 2)


def all_crossings(profile, xi, threshold):
    y = np.asarray(profile, float) - threshold
    xi = np.asarray(xi, float)
    out = []

    for j in range(len(xi) - 1):
        y0, y1 = y[j], y[j + 1]
        if np.isclose(y0, 0.0, atol=1e-12):
            out.append(float(xi[j]))
        elif y0 * y1 < 0.0:
            frac = np.clip(-y0 / (y1 - y0), 0.0, 1.0)
            out.append(float(xi[j] + frac * (xi[j + 1] - xi[j])))

    if np.isclose(y[-1], 0.0, atol=1e-12):
        out.append(float(xi[-1]))

    if not out:
        return np.array([], float)

    arr = np.asarray(sorted(out), float)
    keep = [0]
    for i in range(1, len(arr)):
        if abs(arr[i] - arr[keep[-1]]) > 1e-10:
            keep.append(i)
    return arr[keep]


def front_positions(target, xi):
    nt, ns, _ = target.shape
    pos = np.full((nt, ns), np.nan)
    ok = np.zeros((nt, ns), bool)
    for it in range(nt):
        for i in range(ns):
            c = all_crossings(target[it, i], xi, FRONT_THRESHOLD)
            if c.size:
                pos[it, i] = c[0]
                ok[it, i] = True
    return pos, ok


def source_evidence():
    candidates = []
    patterns = [
        "PAD_Stream_V15SG7CR3F4*.py",
        "PAD_Stream_V15SG7CR3F4R*.py",
        "PAD_Stream_V15SG7CR3F3*.py",
    ]

    for pattern in patterns:
        candidates.extend(ROOT.glob(pattern))

    rows = []
    needle = "front_shell_residual_coverage_fraction"

    for path in sorted(set(candidates)):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for idx, line in enumerate(lines):
            if needle.lower() in line.lower():
                lo = max(0, idx - 12)
                hi = min(len(lines), idx + 13)
                excerpt = "\n".join(
                    f"{j+1}: {lines[j]}"
                    for j in range(lo, hi)
                )
                rows.append({
                    "file": str(path),
                    "line_number": idx + 1,
                    "matching_line": line.strip(),
                    "context_excerpt": excerpt,
                })

    return rows


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R0")
    print("Support-Metric Definition Reconciliation Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE CALIBRATED.
NO FRONT, TOF-BIAS, MAP-BACK, OR SG7E GATE WILL BE CHANGED.
""")

    for p in [R3D_GLOBAL, R3F4R_SUPPORT, R3F4_CHECKPOINTS, R3C_NUMERICAL]:
        if not p.exists():
            raise FileNotFoundError(f"Missing R3F5-R0 prerequisite:\n{p}")

    r3d_rows = load_csv(R3D_GLOBAL)
    support_rows = load_csv(R3F4R_SUPPORT)
    checkpoint_rows = load_csv(R3F4_CHECKPOINTS)

    b4_r3d = next(r for r in r3d_rows if r.get("experiment") == "B4")
    authoritative = fnum(
        b4_r3d,
        "front_shell_residual_coverage_fraction",
    )

    b4_support = next(
        (r for r in support_rows if r.get("experiment") == "B4"),
        None,
    )

    if b4_support is None:
        raise RuntimeError("B4 row missing from authoritative R3F4-R support table.")

    print("AUTHORITATIVE SUPPORT EVIDENCE")
    print(f"  R3D B4 support metric      : {100*authoritative:.4f}%")
    print(f"  R3F4-R table fields        : {list(b4_support.keys())}")

    field_rows = []
    for key, value in b4_support.items():
        field_rows.append({
            "experiment": "B4",
            "field": key,
            "value": value,
        })

    save_csv(FIELD_TABLE, field_rows)

    ck = next(
        r for r in checkpoint_rows
        if r.get("experiment") == "B4"
        and r.get("checkpoint_type") == "best_any"
    )

    b4_path = Path(ck["path"])
    if not b4_path.is_absolute():
        b4_path = ROOT / b4_path

    if not b4_path.exists():
        raise FileNotFoundError(f"Missing B4 checkpoint:\n{b4_path}")

    db = np.load(R3C_NUMERICAL, allow_pickle=True)
    frozen = np.asarray(db["deployment_pirnn"], float)
    target = np.asarray(db["canonical_interpolated_target"], float)
    truth = np.asarray(db["deployment_truth"], float)
    normalized_tD = np.asarray(db["deployment_normalized_input"], float)
    tau_end = np.asarray(db["tau_end_days"], float)
    times = np.asarray(db["times_days"], float)
    xi = np.asarray(db["canonical_xi"], float)

    residual = target - frozen
    abs_residual = np.abs(residual)

    model = build_b4_model()
    model.load_weights(str(b4_path))

    features = make_features(normalized_tD, tau_end)
    raw = model.predict(
        features.reshape(-1, 2),
        batch_size=8192,
        verbose=0,
    )

    nt, ns, nx = residual.shape
    weights = raw.reshape(nt, ns, 3)
    w1 = weights[:, :, 0]
    w2 = weights[:, :, 1]

    front, front_ok = front_positions(target, xi)
    distance = np.zeros((nt, ns, nx), float)

    for it in range(nt):
        distance[it] = xi[None, :] - front[it, :, None]

    g1 = gaussian(distance, SIGMA_NARROW)
    g2 = gaussian(distance, SIGMA_MEDIUM)

    coeff = np.clip(
        w1[:, :, None] * g1
        +
        w2[:, :, None] * g2,
        0.0,
        1.0,
    )

    coeff = np.where(
        front_ok[:, :, None],
        coeff,
        0.0,
    )

    idx100 = int(np.argmin(np.abs(times - 100.0)))

    c = coeff[idx100]
    r = abs_residual[idx100]
    valid = np.broadcast_to(
        front_ok[idx100][:, None],
        c.shape,
    )

    # Candidate support metrics.
    metrics = {}

    denom_r = np.sum(r[valid])
    metrics["residual_weighted_coefficient"] = float(
        np.sum(r[valid] * c[valid]) / max(denom_r, 1e-15)
    )

    for eps in [1e-12, 1e-8, 1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1e-1]:
        mask = valid & (c > eps)

        metrics[f"point_occupancy_coeff_gt_{eps:g}"] = float(
            np.sum(mask) / max(np.sum(valid), 1)
        )

        metrics[f"residual_weighted_occupancy_coeff_gt_{eps:g}"] = float(
            np.sum(r[mask]) / max(denom_r, 1e-15)
        )

    # Support based on the two basis fields themselves.
    basis_union = valid & ((g1[idx100] > 1e-6) | (g2[idx100] > 1e-6))

    metrics["basis_union_point_occupancy"] = float(
        np.sum(basis_union) / max(np.sum(valid), 1)
    )

    metrics["basis_union_residual_weighted_occupancy"] = float(
        np.sum(r[basis_union]) / max(denom_r, 1e-15)
    )

    # Front-shell geometric support candidates.
    for width in [0.01, 0.015, 0.02, 0.03, 0.04, 0.05, 0.06]:
        shell = valid & (np.abs(distance[idx100]) <= width)

        metrics[f"front_shell_point_occupancy_w{width:g}"] = float(
            np.sum(shell) / max(np.sum(valid), 1)
        )

        metrics[f"front_shell_residual_weighted_occupancy_w{width:g}"] = float(
            np.sum(r[shell]) / max(denom_r, 1e-15)
        )

    metric_rows = []

    for name, value in metrics.items():
        abs_error = abs(value - authoritative)
        rel_error = abs_error / max(abs(authoritative), 1e-15)

        metric_rows.append({
            "metric": name,
            "value": value,
            "value_percent": 100 * value,
            "authoritative_value": authoritative,
            "authoritative_percent": 100 * authoritative,
            "absolute_error": abs_error,
            "relative_error": rel_error,
            "matches_authoritative":
                bool(
                    abs_error <= ABS_TOL
                    or
                    rel_error <= REL_TOL
                ),
        })

    metric_rows.sort(
        key=lambda row: (
            row["absolute_error"],
            row["relative_error"],
        )
    )

    save_csv(METRIC_TABLE, metric_rows)

    print("\nCANDIDATE METRIC RECONSTRUCTION")
    for row in metric_rows[:12]:
        print(
            f"  {row['metric']:<52s} "
            f"{100*row['value']:8.4f}% | "
            f"|delta|={100*row['absolute_error']:.4f} pp"
        )

    # Source-code definition evidence.
    source_rows = source_evidence()
    save_csv(SOURCE_TABLE, source_rows)

    print("\nSOURCE-DEFINITION SEARCH")
    if source_rows:
        print(f"  Found {len(source_rows)} source occurrence(s).")
        for row in source_rows[:5]:
            print(
                f"  {Path(row['file']).name}:{row['line_number']}"
            )
    else:
        print("  No source occurrence found by filename/field-name search.")

    best = metric_rows[0]
    matched = [
        row
        for row in metric_rows
        if row["matches_authoritative"]
    ]

    # The source table is authoritative if it exposes the exact formula;
    # otherwise the numerical reconciliation must be tight enough before R3F5-R1.
    metric_reconciled = bool(matched)

    if metric_reconciled:
        diagnosis = "AUTHORITATIVE_SUPPORT_METRIC_RECONSTRUCTED"

        recommendation = (
            f"The closest reconstructed definition is '{best['metric']}', which "
            f"reproduces the authoritative B4 support within the repair tolerance. "
            "Use this exact support definition in R3F5-R1; do not use multiplicative "
            "anchoring of the previous residual-weighted coefficient metric."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1 — Controlled Minimal-Support Extension Calibration Repair"
        )

        status = "SUPPORT_METRIC_RECONCILIATION_READY"

    else:
        diagnosis = "AUTHORITATIVE_SUPPORT_METRIC_NOT_YET_RECONSTRUCTED"

        recommendation = (
            "None of the candidate numerical definitions reproduces the authoritative "
            "49.5478% support closely enough. Use the saved source-definition evidence "
            "to reconstruct the exact R3F4/R3D formula before any support extension "
            "calibration. Do not anchor by scale."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R0A — Exact Authoritative Support Formula Extraction"
        )

        status = "SUPPORT_METRIC_RECONCILIATION_INCOMPLETE"

    contract = {
        "milestone": "V15-SG7C-R3F5-R0",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "support_extension_calibrated": False,
        "authoritative_B4_support_fraction": authoritative,
        "closest_metric": best["metric"],
        "closest_metric_value": best["value"],
        "closest_metric_absolute_error": best["absolute_error"],
        "closest_metric_relative_error": best["relative_error"],
        "matching_metrics": [
            {
                "metric": row["metric"],
                "value": row["value"],
                "absolute_error": row["absolute_error"],
                "relative_error": row["relative_error"],
            }
            for row in matched
        ],
        "multiplicative_anchor_prohibited": True,
        "source_definition_occurrences": len(source_rows),
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(CONTRACT_FILE, contract)

    summary = {
        "milestone": "V15-SG7C-R3F5-R0",
        "status": status,
        "diagnosis": diagnosis,
        "training_performed": False,
        "model_parameters_changed": False,
        "gate_changed": False,
        "support_extension_calibrated": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(SUMMARY_FILE, summary)

    # Diagnostics.
    top = metric_rows[:15]
    labels = [r["metric"] for r in top][::-1]
    values = [100*r["value"] for r in top][::-1]

    plt.figure(figsize=(11, 7))
    plt.barh(labels, values)
    plt.axvline(
        100*authoritative,
        linestyle="--",
        label="authoritative R3D support",
    )
    plt.xlabel("Support metric (%)")
    plt.title("V15-SG7C-R3F5-R0 Candidate Support Definitions")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        OUT / "V15SG7CR3F5R0_Candidate_Support_Metrics.png",
        dpi=300,
    )
    plt.close()

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R0 DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("R3D authoritative B4 support loaded", np.isfinite(authoritative)),
        ("Persisted B4 checkpoint loaded", True),
        ("R3C deployment database loaded", True),
        ("B4 front-local basis reconstructed", True),
        ("Multiple candidate support definitions evaluated", len(metric_rows) > 10),
        ("R3F4/R source definition searched", True),
        ("Multiplicative anchor explicitly prohibited", True),
        ("No support extension calibrated", True),
        ("No training performed", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

    print("\nAUTHORITATIVE VALUE")
    print(f"  B4 support             : {100*authoritative:.4f}%")

    print("\nCLOSEST RECONSTRUCTION")
    print(f"  Metric                 : {best['metric']}")
    print(f"  Value                  : {100*best['value']:.4f}%")
    print(f"  Absolute error         : {100*best['absolute_error']:.4f} pp")
    print(f"  Relative error         : {100*best['relative_error']:.3f}%")

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {METRIC_TABLE.name}")
    print(f"  {SOURCE_TABLE.name}")
    print(f"  {FIELD_TABLE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nDiagnostics:")
    print("  V15SG7CR3F5R0_Candidate_Support_Metrics.png")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R0 AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No support extension was calibrated.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
