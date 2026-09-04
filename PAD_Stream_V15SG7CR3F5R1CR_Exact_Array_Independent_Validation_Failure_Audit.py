from __future__ import annotations

from pathlib import Path
import csv
import json
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1CR
# Exact-Array Independent Validation Failure Audit
#
# DIAGNOSTIC MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO SUPPORT EXTENSION RECALIBRATED.
# NO FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1C independently validated the nominated X08 exact-array support extension.
#
# X08 PASSED:
#   * exact support >= 50%
#   * recovered fronts
#   * conditioned front gap
#   * 100d profile L1
#   * coefficient bounds
#   * canonical-direction monotonicity
#
# X08 FAILED:
#   * bias_500_1000
#   * bias_1000_2000
#   * bias_gt2000
#   * tail_bias
#   * material_positive_share_500_1000
#
# This audit determines whether those TOF/tail failures:
#
#   A) already existed in the unextended B4 baseline,
#   B) were materially worsened by X08,
#   C) are localized specifically to shoulder-activated nodes,
#   D) are concentrated in long-TOF populations,
#   E) are structurally incompatible with a uniform geometric shoulder.
#
# The milestone does NOT alter eta or support geometry.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1CR"
OUT.mkdir(parents=True, exist_ok=True)

R1C_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1C"
    / "PAD_Stream_V15SG7CR3F5R1C_Summary.json"
)

R1C_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1C"
    / "V15SG7CR3F5R1C_Independent_Validation.npz"
)

R1B_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Exact_Array_Extension_Results.npz"
)

R1B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Candidate_Manifest.json"
)

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1CR_Summary.json"
GLOBAL_TABLE = OUT / "V15SG7CR3F5R1CR_Global_Bias_Comparison.csv"
TOF_TABLE = OUT / "V15SG7CR3F5R1CR_TOF_Band_Bias_Comparison.csv"
SHOULDER_TABLE = OUT / "V15SG7CR3F5R1CR_Shoulder_Contribution_By_TOF.csv"
TAIL_TABLE = OUT / "V15SG7CR3F5R1CR_Tail_Bias_Decomposition.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1CR_Failed_Gate_Decomposition.csv"
NUMERICAL_FILE = OUT / "V15SG7CR3F5R1CR_Bias_Decomposition.npz"
CONTRACT_FILE = OUT / "V15SG7CR3F5R1CR_Failure_Audit_Contract.json"

# Unchanged authoritative limits.
BIAS_500_1000_MAX = 2.5e-3
BIAS_1000_2000_MAX = 4.5e-3
BIAS_GT2000_MAX = 5.0e-3
TAIL_BIAS_MAX = 5.0e-3
MATERIAL_SHARE_MAX = 0.40

TAIL_THRESHOLD = 0.22
MATERIAL_POSITIVE_THRESHOLD = 0.005
EPS = 1e-15


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload):
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_csv(path: Path, rows):
    if not rows:
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def band_mask(tau_end, lo, hi):
    return (tau_end > lo) & (tau_end <= hi)


def band_metrics(truth, base, cand, tau_end, label, lo, hi):
    mask = band_mask(tau_end, lo, hi)

    if not np.any(mask):
        return {
            "band": label,
            "streamlines": 0,
            "base_bias": np.nan,
            "candidate_bias": np.nan,
            "delta_bias": np.nan,
            "base_L1": np.nan,
            "candidate_L1": np.nan,
            "delta_L1": np.nan,
        }

    dbase = base[mask] - truth[mask]
    dcand = cand[mask] - truth[mask]

    return {
        "band": label,
        "streamlines": int(np.sum(mask)),
        "base_bias": float(np.mean(dbase)),
        "candidate_bias": float(np.mean(dcand)),
        "delta_bias": float(np.mean(dcand - dbase)),
        "base_L1": float(np.mean(np.abs(dbase))),
        "candidate_L1": float(np.mean(np.abs(dcand))),
        "delta_L1": float(np.mean(np.abs(dcand)) - np.mean(np.abs(dbase))),
    }


def material_positive_share(diff):
    return float(np.mean(diff > MATERIAL_POSITIVE_THRESHOLD))


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1CR")
    print("Exact-Array Independent Validation Failure Audit")
    print("=" * 78)

    print("""
NO TRAINING WILL BE PERFORMED.
NO MODEL PARAMETERS WILL BE CHANGED.
NO SUPPORT EXTENSION WILL BE RECALIBRATED.
NO FRONT OR TOF-BIAS GATE WILL BE CHANGED OR RELAXED.
NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.
""")

    incoming = load_json(R1C_SUMMARY)

    if incoming.get("diagnosis") != "X08_FAILS_ONE_OR_MORE_INDEPENDENT_DEPLOYMENT_GATES":
        raise RuntimeError(
            "R1CR requires incoming R1C independent-validation failure diagnosis."
        )

    manifest = load_json(R1B_MANIFEST)

    selected = manifest.get("selected_experiment")

    if selected != "X08":
        raise RuntimeError(f"Expected X08 candidate, got {selected!r}")

    r1c = np.load(R1C_NUMERICAL, allow_pickle=True)
    r1b = np.load(R1B_NUMERICAL, allow_pickle=True)

    required_r1c = [
        "truth100",
        "base100",
        "candidate100",
        "tau_end",
        "coeff100_base",
        "coeff100_candidate",
    ]

    for key in required_r1c:
        if key not in r1c.files:
            raise RuntimeError(f"R1C numerical database missing key: {key}")

    truth = np.asarray(r1c["truth100"], dtype=float)
    base = np.asarray(r1c["base100"], dtype=float)
    cand = np.asarray(r1c["candidate100"], dtype=float)
    tau_end = np.asarray(r1c["tau_end"], dtype=float)

    coeff_base = np.asarray(r1c["coeff100_base"], dtype=float)
    coeff_cand = np.asarray(r1c["coeff100_candidate"], dtype=float)

    if "shoulder_mask" not in r1b.files or "shoulder_strength" not in r1b.files:
        raise RuntimeError("R1B numerical database missing shoulder geometry arrays.")

    shoulder_mask = np.asarray(r1b["shoulder_mask"], dtype=bool)
    shoulder_strength = np.asarray(r1b["shoulder_strength"], dtype=float)

    if not (
        truth.shape == base.shape == cand.shape
        and truth.ndim == 2
    ):
        raise RuntimeError("Expected 100d state arrays with common shape (nstream,nxi).")

    nstream, nxi = truth.shape

    if tau_end.size != nstream:
        raise RuntimeError("tau_end length does not match streamline count.")

    if shoulder_mask.shape != truth.shape:
        raise RuntimeError(
            f"shoulder_mask shape {shoulder_mask.shape} != truth shape {truth.shape}"
        )

    base_diff = base - truth
    cand_diff = cand - truth
    extension_delta = cand - base
    coeff_delta = coeff_cand - coeff_base

    global_rows = [{
        "metric": "global_bias",
        "base": float(np.mean(base_diff)),
        "candidate": float(np.mean(cand_diff)),
        "delta": float(np.mean(extension_delta)),
    }, {
        "metric": "global_L1",
        "base": float(np.mean(np.abs(base_diff))),
        "candidate": float(np.mean(np.abs(cand_diff))),
        "delta": float(np.mean(np.abs(cand_diff)) - np.mean(np.abs(base_diff))),
    }, {
        "metric": "global_L2",
        "base": float(np.sqrt(np.mean(base_diff**2))),
        "candidate": float(np.sqrt(np.mean(cand_diff**2))),
        "delta": float(
            np.sqrt(np.mean(cand_diff**2))
            - np.sqrt(np.mean(base_diff**2))
        ),
    }]

    save_csv(GLOBAL_TABLE, global_rows)

    bands = [
        ("<=250d", -np.inf, 250.0),
        ("250-500d", 250.0, 500.0),
        ("500-1000d", 500.0, 1000.0),
        ("1000-2000d", 1000.0, 2000.0),
        (">2000d", 2000.0, np.inf),
    ]

    tof_rows = []

    for label, lo, hi in bands:
        tof_rows.append(
            band_metrics(
                truth,
                base,
                cand,
                tau_end,
                label,
                lo,
                hi,
            )
        )

    save_csv(TOF_TABLE, tof_rows)

    # -------------------------------------------------------------------------
    # Shoulder-specific contribution by TOF.
    # -------------------------------------------------------------------------

    shoulder_rows = []

    for label, lo, hi in bands:
        smask = band_mask(tau_end, lo, hi)

        if not np.any(smask):
            continue

        local_shoulder = shoulder_mask[smask]
        local_delta = extension_delta[smask]
        local_coeff_delta = coeff_delta[smask]

        active = local_shoulder & (np.abs(local_coeff_delta) > 1e-14)

        if np.any(active):
            mean_state_delta = float(np.mean(local_delta[active]))
            mean_abs_state_delta = float(np.mean(np.abs(local_delta[active])))
            mean_coeff_delta = float(np.mean(local_coeff_delta[active]))
            active_nodes = int(np.sum(active))
        else:
            mean_state_delta = np.nan
            mean_abs_state_delta = np.nan
            mean_coeff_delta = np.nan
            active_nodes = 0

        total_abs_extension = float(
            np.sum(
                np.abs(
                    local_delta
                )
            )
        )

        shoulder_abs_extension = float(
            np.sum(
                np.abs(
                    local_delta[active]
                )
            )
        ) if np.any(active) else 0.0

        share = (
            shoulder_abs_extension / max(total_abs_extension, EPS)
        )

        shoulder_rows.append({
            "band": label,
            "streamlines": int(np.sum(smask)),
            "active_shoulder_nodes": active_nodes,
            "mean_state_delta_on_active_shoulder": mean_state_delta,
            "mean_abs_state_delta_on_active_shoulder": mean_abs_state_delta,
            "mean_coeff_delta_on_active_shoulder": mean_coeff_delta,
            "shoulder_share_of_abs_extension": share,
        })

    save_csv(SHOULDER_TABLE, shoulder_rows)

    # -------------------------------------------------------------------------
    # Tail decomposition.
    # -------------------------------------------------------------------------

    tail_mask = truth <= TAIL_THRESHOLD

    base_tail_bias = float(np.mean(base_diff[tail_mask]))
    cand_tail_bias = float(np.mean(cand_diff[tail_mask]))
    delta_tail_bias = float(np.mean(extension_delta[tail_mask]))

    tail_shoulder = tail_mask & shoulder_mask
    nonshoulder_tail = tail_mask & (~shoulder_mask)

    tail_rows = [{
        "population": "all_tail",
        "nodes": int(np.sum(tail_mask)),
        "base_bias": base_tail_bias,
        "candidate_bias": cand_tail_bias,
        "delta_bias": delta_tail_bias,
    }]

    for label, mask in [
        ("tail_shoulder", tail_shoulder),
        ("tail_nonshoulder", nonshoulder_tail),
    ]:
        if np.any(mask):
            tail_rows.append({
                "population": label,
                "nodes": int(np.sum(mask)),
                "base_bias": float(np.mean(base_diff[mask])),
                "candidate_bias": float(np.mean(cand_diff[mask])),
                "delta_bias": float(np.mean(extension_delta[mask])),
            })

    save_csv(TAIL_TABLE, tail_rows)

    # -------------------------------------------------------------------------
    # Failed-gate decomposition.
    # -------------------------------------------------------------------------

    mask500 = band_mask(tau_end, 500.0, 1000.0)
    mask1000 = band_mask(tau_end, 1000.0, 2000.0)
    mask2000 = band_mask(tau_end, 2000.0, np.inf)

    base_b500 = float(np.mean(base_diff[mask500]))
    cand_b500 = float(np.mean(cand_diff[mask500]))

    base_b1000 = float(np.mean(base_diff[mask1000]))
    cand_b1000 = float(np.mean(cand_diff[mask1000]))

    base_b2000 = float(np.mean(base_diff[mask2000]))
    cand_b2000 = float(np.mean(cand_diff[mask2000]))

    base_material = material_positive_share(base_diff[mask500])
    cand_material = material_positive_share(cand_diff[mask500])

    gate_rows = [
        {
            "gate": "bias_500_1000",
            "limit": BIAS_500_1000_MAX,
            "base_value": base_b500,
            "candidate_value": cand_b500,
            "base_pass": base_b500 <= BIAS_500_1000_MAX,
            "candidate_pass": cand_b500 <= BIAS_500_1000_MAX,
            "extension_delta": cand_b500 - base_b500,
        },
        {
            "gate": "bias_1000_2000",
            "limit": BIAS_1000_2000_MAX,
            "base_value": base_b1000,
            "candidate_value": cand_b1000,
            "base_pass": base_b1000 <= BIAS_1000_2000_MAX,
            "candidate_pass": cand_b1000 <= BIAS_1000_2000_MAX,
            "extension_delta": cand_b1000 - base_b1000,
        },
        {
            "gate": "bias_gt2000",
            "limit": BIAS_GT2000_MAX,
            "base_value": base_b2000,
            "candidate_value": cand_b2000,
            "base_pass": base_b2000 <= BIAS_GT2000_MAX,
            "candidate_pass": cand_b2000 <= BIAS_GT2000_MAX,
            "extension_delta": cand_b2000 - base_b2000,
        },
        {
            "gate": "tail_bias",
            "limit": TAIL_BIAS_MAX,
            "base_value": base_tail_bias,
            "candidate_value": cand_tail_bias,
            "base_pass": base_tail_bias <= TAIL_BIAS_MAX,
            "candidate_pass": cand_tail_bias <= TAIL_BIAS_MAX,
            "extension_delta": cand_tail_bias - base_tail_bias,
        },
        {
            "gate": "material_positive_share_500_1000",
            "limit": MATERIAL_SHARE_MAX,
            "base_value": base_material,
            "candidate_value": cand_material,
            "base_pass": base_material <= MATERIAL_SHARE_MAX,
            "candidate_pass": cand_material <= MATERIAL_SHARE_MAX,
            "extension_delta": cand_material - base_material,
        },
    ]

    save_csv(GATE_TABLE, gate_rows)

    # -------------------------------------------------------------------------
    # Mechanism classification.
    # -------------------------------------------------------------------------

    base_failures = [
        row["gate"]
        for row in gate_rows
        if not row["base_pass"]
    ]

    candidate_failures = [
        row["gate"]
        for row in gate_rows
        if not row["candidate_pass"]
    ]

    newly_created_failures = [
        row["gate"]
        for row in gate_rows
        if row["base_pass"] and not row["candidate_pass"]
    ]

    materially_worsened = [
        row["gate"]
        for row in gate_rows
        if row["candidate_value"] - row["base_value"] > 5e-4
    ]

    # Long-TOF shoulder activity.
    slow_shoulder_rows = [
        row
        for row in shoulder_rows
        if row["band"] in ("500-1000d", "1000-2000d", ">2000d")
    ]

    slow_shoulder_active = any(
        row["active_shoulder_nodes"] > 0
        for row in slow_shoulder_rows
    )

    # Classification hierarchy.
    if (
        len(base_failures) == len(candidate_failures)
        and
        set(base_failures) == set(candidate_failures)
        and
        not materially_worsened
    ):
        status = "R1C_FAILURE_AUDIT_COMPLETE"
        diagnosis = "TOF_BIAS_FAILURES_PREEXIST_SUPPORT_EXTENSION"
        recommendation = (
            "All failed TOF/tail gates were already violated by the unextended B4 exact-array "
            "baseline and X08 does not materially worsen them. The support extension itself is "
            "not the limiting mechanism. Preserve X08 geometry and return to the previously "
            "identified deployment TOF-bias correction problem using the clarified front contract."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1D — Joint Exact-Support / TOF-Bias Reconciliation Design"
        )

    elif newly_created_failures:
        status = "R1C_FAILURE_AUDIT_COMPLETE"
        diagnosis = "SUPPORT_EXTENSION_CREATES_NEW_TOF_BIAS_REGRESSION"
        recommendation = (
            "X08 crosses the support gate but introduces one or more new TOF/tail failures. "
            "Do not change the gate. Redesign the shoulder so long-TOF/tail populations receive "
            "less or no support extension while preserving the exact 50% support target."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1D — TOF-Conditioned Exact-Support Shoulder Design"
        )

    elif materially_worsened and slow_shoulder_active:
        status = "R1C_FAILURE_AUDIT_COMPLETE"
        diagnosis = "UNIFORM_SHOULDER_AMPLIFIES_PREEXISTING_SLOW_TOF_BIAS"
        recommendation = (
            "The failed TOF/tail gates preexist, but the uniform X08 shoulder materially worsens "
            "one or more slow-TOF populations. Preserve the exact-array formulation and redesign "
            "only the shoulder weighting to suppress correction in slow-TOF/tail regions."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1D — TOF-Conditioned Exact-Support Shoulder Design"
        )

    else:
        status = "R1C_FAILURE_AUDIT_COMPLETE"
        diagnosis = "COUPLED_SUPPORT_TOF_BIAS_LIMITER"
        recommendation = (
            "The independent failure combines preexisting TOF bias with support-extension effects. "
            "Do not retrain the transport model or relax gates. Design a joint exact-support / "
            "TOF-conditioned correction contract using this decomposition."
        )
        next_milestone = (
            "V15-SG7C-R3F5-R1D — Joint Exact-Support / TOF-Bias Reconciliation Design"
        )

    np.savez_compressed(
        NUMERICAL_FILE,
        truth100=truth.astype(np.float32),
        base100=base.astype(np.float32),
        candidate100=cand.astype(np.float32),
        extension_delta=extension_delta.astype(np.float32),
        coeff_delta=coeff_delta.astype(np.float32),
        shoulder_mask=shoulder_mask.astype(np.uint8),
        shoulder_strength=shoulder_strength.astype(np.float32),
        tau_end=tau_end.astype(np.float64),
    )

    save_json(
        CONTRACT_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1CR",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_recalibrated": False,
            "gate_changed": False,
            "base_failures": base_failures,
            "candidate_failures": candidate_failures,
            "newly_created_failures": newly_created_failures,
            "materially_worsened_failures": materially_worsened,
            "slow_TOF_shoulder_active": slow_shoulder_active,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1CR",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "support_extension_recalibrated": False,
            "gate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\n" + "=" * 78)
    print("FAILED-GATE BASELINE VS X08")
    print("=" * 78)

    for row in gate_rows:
        print(
            f"{row['gate']:<38s} | "
            f"base={row['base_value']:.6e} | "
            f"X08={row['candidate_value']:.6e} | "
            f"delta={row['extension_delta']:+.6e} | "
            f"base={'PASS' if row['base_pass'] else 'FAIL'} | "
            f"X08={'PASS' if row['candidate_pass'] else 'FAIL'}"
        )

    print("\nDIAGNOSTIC FLAGS")
    print(f"  Base failures           : {len(base_failures)}")
    print(f"  Candidate failures      : {len(candidate_failures)}")
    print(f"  Newly created failures  : {len(newly_created_failures)}")
    print(f"  Materially worsened     : {len(materially_worsened)}")
    print(f"  Slow-TOF shoulder active: {slow_shoulder_active}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1CR DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        ("Incoming R1C failure diagnosis reproduced", True),
        ("X08 identity reproduced", True),
        ("Base and candidate 100d fields loaded", True),
        ("R1B shoulder geometry loaded", True),
        ("Base TOF/tail gates recomputed", True),
        ("Candidate TOF/tail gates recomputed", True),
        ("Shoulder contribution stratified by TOF", True),
        ("Tail bias decomposed by shoulder activity", True),
        ("No support extension recalibrated", True),
        ("No gate changed or relaxed", True),
        ("No training performed", True),
        ("Failure mechanism classified", True),
    ]

    for desc, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {desc}")

    print("=" * 78)

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
    print(f"  {GLOBAL_TABLE.name}")
    print(f"  {TOF_TABLE.name}")
    print(f"  {SHOULDER_TABLE.name}")
    print(f"  {TAIL_TABLE.name}")
    print(f"  {GATE_TABLE.name}")

    print("\nNumerical:")
    print(f"  {NUMERICAL_FILE.name}")

    print("\nContract:")
    print(f"  {CONTRACT_FILE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1CR FAILURE AUDIT: COMPLETE")
    print()
    print("No training was performed.")
    print("No support extension was recalibrated.")
    print("No gate was changed or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
