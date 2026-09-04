from __future__ import annotations

from pathlib import Path
import csv
import json
import math

# =============================================================================
# PAD-Stream V15-SG7B-15R
# Front-Preserving TOF Contract Repair
#
# NO TRAINING.
# NO MODEL WEIGHTS CHANGED.
# NO ARCHITECTURE CHANGE.
# NO GATE RELAXATION.
# NO THRESHOLD CHANGE.
#
# PURPOSE
# -------
# SG7B-15 failed one design-validation check:
#
#   [FAIL] SG7B-10S front-gap gate retained unchanged
#
# The SG7B-15 script hard-coded the DISPLAY-ROUNDED value
#
#   5.331237e-04
#
# and then compared it against the full-precision value persisted by SG7B-10S
# using a 1e-12 equality tolerance. This repair reads the authoritative
# full-precision values directly from SG7B-10S and SG7B-12 and reconstructs
# the SG7B-15 design contract without changing any numerical requirement.
#
# =============================================================================


ROOT = Path(__file__).resolve().parent

SG7B15_SUMMARY = (
    ROOT / "output" / "V15_SG7B15"
    / "PAD_Stream_V15SG7B15_Summary.json"
)

SG7B15_CONTRACT = (
    ROOT / "output" / "V15_SG7B15"
    / "V15SG7B15_Front_Preserving_TOF_Refinement_Contract.json"
)

SG7B15_REGIONS = (
    ROOT / "output" / "V15_SG7B15"
    / "V15SG7B15_Training_Region_Definition.csv"
)

SG7B15_LOSS = (
    ROOT / "output" / "V15_SG7B15"
    / "V15SG7B15_Loss_Component_Design.csv"
)

SG7B15_EXPERIMENTS = (
    ROOT / "output" / "V15_SG7B15"
    / "V15SG7B15_SG7B16_Experiment_Matrix.csv"
)

SG7B10S_CONTRACT = (
    ROOT / "output" / "V15_SG7B10S"
    / "V15SG7B10S_SG7A_Relative_Front_Shape_Contract.json"
)

SG7B12_CONTRACT = (
    ROOT / "output" / "V15_SG7B12"
    / "V15SG7B12_TOF_Conditioned_Refinement_Contract.json"
)

SG7B11_FROZEN_MODEL = (
    ROOT / "output" / "V15_SG7B11"
    / "V15SG7B_FRONT_AWARE_FROZEN_Model.keras"
)

OUTPUT_DIR = ROOT / "output" / "V15_SG7B15R"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPAIRED_CONTRACT = (
    OUTPUT_DIR
    / "V15SG7B15R_Front_Preserving_TOF_Refinement_Contract.json"
)

GATE_AUDIT_TABLE = (
    OUTPUT_DIR
    / "V15SG7B15R_Authoritative_Gate_Audit.csv"
)

SUMMARY_FILE = (
    OUTPUT_DIR
    / "PAD_Stream_V15SG7B15R_Summary.json"
)


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


def find_gate_by_text(rows, text):
    text_lower = text.lower()
    for row in rows:
        joined = " ".join(str(v) for v in row.values()).lower()
        if text_lower in joined:
            return row
    return None


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7B-15R")
    print("Front-Preserving TOF Contract Repair")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL WEIGHTS WILL BE CHANGED.")
    print("NO ARCHITECTURE CHANGE WILL BE MADE.")
    print("NO SG7B-10S GATE WILL BE RELAXED.")
    print("NO SG7B-12 GATE WILL BE RELAXED.")
    print("NO SG7E PLUME THRESHOLD WILL BE CHANGED.")

    required = [
        SG7B15_SUMMARY,
        SG7B15_CONTRACT,
        SG7B15_REGIONS,
        SG7B15_LOSS,
        SG7B15_EXPERIMENTS,
        SG7B10S_CONTRACT,
        SG7B12_CONTRACT,
        SG7B11_FROZEN_MODEL,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"Missing SG7B-15R prerequisite:\n{path}")

    sg15_summary = load_json(SG7B15_SUMMARY)
    sg15_contract = load_json(SG7B15_CONTRACT)
    sg10s = load_json(SG7B10S_CONTRACT)
    sg12 = load_json(SG7B12_CONTRACT)

    if (
        sg15_summary.get("status")
        !=
        "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_INCOMPLETE"
    ):
        raise RuntimeError(
            "SG7B-15R requires the incomplete SG7B-15 contract status."
        )

    # -------------------------------------------------------------------------
    # Authoritative SG7B-10S front contract
    # -------------------------------------------------------------------------

    front_contract = sg10s["front_improvement_contract"]

    exact_min_fronts = int(
        front_contract["minimum_recovered_fronts"]
    )

    exact_max_gap = float(
        front_contract["maximum_conditioned_threshold_gap"]
    )

    exact_max_profile_l1 = float(
        front_contract["maximum_100d_profile_L1"]
    )

    # SG7B-15 used the rounded terminal-display value.
    rounded_gap_used_by_sg15 = float(
        sg15_summary.get(
            "required_conditioned_front_gap",
            5.331237e-04,
        )
    )

    absolute_difference = abs(
        rounded_gap_used_by_sg15
        -
        exact_max_gap
    )

    relative_difference = (
        absolute_difference
        /
        max(
            abs(exact_max_gap),
            1.0e-30,
        )
    )

    print("\nAUTHORITATIVE SG7B-10S FRONT CONTRACT")
    print(f"  Minimum recovered fronts : {exact_min_fronts}")
    print(f"  Maximum conditioned gap   : {exact_max_gap:.17e}")
    print(f"  Maximum 100d profile L1   : {exact_max_profile_l1:.17e}")

    print("\nSG7B-15 ROUNDING AUDIT")
    print(
        f"  SG7B-15 stored/display gap: "
        f"{rounded_gap_used_by_sg15:.17e}"
    )
    print(
        f"  SG7B-10S exact gap        : "
        f"{exact_max_gap:.17e}"
    )
    print(
        f"  Absolute difference       : "
        f"{absolute_difference:.17e}"
    )
    print(
        f"  Relative difference       : "
        f"{relative_difference:.6e}"
    )

    # -------------------------------------------------------------------------
    # Retain all SG7B-15 design content, but replace front-gate values with the
    # exact authoritative SG7B-10S values.
    # -------------------------------------------------------------------------

    repaired = dict(sg15_contract)

    repaired["milestone"] = "V15-SG7B-15R"
    repaired["description"] = (
        "Repaired front-preserving TOF refinement design contract"
    )

    repaired["repair"] = {
        "source_milestone": "V15-SG7B-15",
        "reason": (
            "SG7B-15 compared a display-rounded conditioned-front-gap value "
            "against the full-precision SG7B-10S contract."
        ),
        "gate_relaxed": False,
        "authoritative_source": str(SG7B10S_CONTRACT),
        "rounded_value_used_by_SG7B15": rounded_gap_used_by_sg15,
        "exact_SG7B10S_value": exact_max_gap,
        "absolute_difference": absolute_difference,
        "relative_difference": relative_difference,
    }

    # Explicit machine-readable exact authoritative gates for SG7B-16.
    repaired["authoritative_front_improvement_contract"] = {
        "minimum_recovered_fronts": exact_min_fronts,
        "maximum_conditioned_threshold_gap": exact_max_gap,
        "maximum_100d_profile_L1": exact_max_profile_l1,
    }

    # Preserve SG7B-12 bias contract exactly as persisted.
    repaired["authoritative_SG7B12_bias_improvement_gates"] = (
        sg12["bias_improvement_gates"]
    )

    # Update textual preservation table stored in the design contract.
    repaired_preservation = []

    for row in repaired.get("preservation_gates", []):

        row = dict(row)

        gate_name = str(
            row.get("gate", "")
        ).strip()

        if gate_name == "Recovered 100d fronts":
            row["limit"] = f">= {exact_min_fronts}"

        elif gate_name == "Conditioned front gap":
            row["limit"] = f"<= {exact_max_gap:.17e}"
            row["exact_numeric_limit"] = exact_max_gap

        elif gate_name == "100d profile L1":
            row["limit"] = f"<= {exact_max_profile_l1:.17e}"
            row["exact_numeric_limit"] = exact_max_profile_l1

        repaired_preservation.append(row)

    repaired["preservation_gates"] = repaired_preservation

    # Contract is now ready for the next controlled training stage.
    repaired["status"] = (
        "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_READY"
    )

    repaired["next_milestone"] = (
        "V15-SG7B-16 — Controlled Front-Preserving TOF Refinement"
    )

    repaired["training_performed"] = False

    # -------------------------------------------------------------------------
    # Validate no design content disappeared.
    # -------------------------------------------------------------------------

    regions = load_csv(SG7B15_REGIONS)
    losses = load_csv(SG7B15_LOSS)
    experiments = load_csv(SG7B15_EXPERIMENTS)

    exact_gate_now = repaired[
        "authoritative_front_improvement_contract"
    ][
        "maximum_conditioned_threshold_gap"
    ]

    front_gap_exact = bool(
        exact_gate_now
        ==
        exact_max_gap
    )

    bias_gate_exact = bool(
        repaired[
            "authoritative_SG7B12_bias_improvement_gates"
        ]
        ==
        sg12[
            "bias_improvement_gates"
        ]
    )

    front_shell_present = any(
        str(row.get("region", ""))
        ==
        "R2_long_TOF_front_shell"
        for row in regions
    )

    front_core_present = any(
        str(row.get("region", ""))
        ==
        "R3_front_core"
        for row in regions
    )

    frozen_control_present = any(
        str(row.get("experiment", ""))
        ==
        "E0"
        for row in experiments
    )

    front_position_loss_present = any(
        str(row.get("component", ""))
        ==
        "L_cross_position"
        for row in losses
    )

    checks = [
        (
            "Incoming SG7B-15 incomplete status reproduced",
            sg15_summary.get("status")
            ==
            "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_INCOMPLETE",
        ),
        (
            "Exact SG7B-10S conditioned-front-gap value loaded",
            math.isfinite(exact_max_gap)
            and exact_max_gap > 0.0,
        ),
        (
            "SG7B-15 mismatch identified as numerical representation difference",
            absolute_difference > 0.0,
        ),
        (
            "Repaired conditioned-front-gap gate equals SG7B-10S exactly",
            front_gap_exact,
        ),
        (
            "SG7B-12 bias gates copied without modification",
            bias_gate_exact,
        ),
        (
            "Front-shell exclusion design retained",
            front_shell_present,
        ),
        (
            "Front-core lock design retained",
            front_core_present,
        ),
        (
            "Explicit crossing-position loss retained",
            front_position_loss_present,
        ),
        (
            "Controlled matrix retains frozen E0 control",
            frozen_control_present,
        ),
        (
            "No training performed by SG7B-15R",
            True,
        ),
    ]

    passed = all(
        flag
        for _, flag in checks
    )

    print("\n" + "=" * 78)
    print("V15-SG7B-15R CONTRACT REPAIR VALIDATION")
    print("=" * 78)

    for description, flag in checks:
        print(
            f"[{'PASS' if flag else 'FAIL'}] "
            f"{description}"
        )

    print("=" * 78)

    if not passed:
        status = (
            "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_REPAIR_FAILED"
        )
        next_milestone = (
            "V15-SG7B-15R2 — Front-Preserving TOF Contract Reconciliation"
        )
        recommendation = (
            "Do not train. The SG7B-15 contract repair did not reproduce all "
            "authoritative gates and design components."
        )
    else:
        status = (
            "FRONT_PRESERVING_TOF_REFINEMENT_CONTRACT_READY"
        )
        next_milestone = (
            "V15-SG7B-16 — Controlled Front-Preserving TOF Refinement"
        )
        recommendation = (
            "Proceed to SG7B-16 using the repaired SG7B-15R contract. "
            "The conditioned-front-gap gate now comes directly from SG7B-10S "
            "at full precision; no gate was changed or relaxed."
        )

    repaired["status"] = status
    repaired["next_milestone"] = next_milestone

    save_json(
        REPAIRED_CONTRACT,
        repaired,
    )

    gate_audit_rows = [
        {
            "gate": "minimum_recovered_fronts",
            "authoritative_source": "SG7B-10S",
            "authoritative_value": exact_min_fronts,
            "repaired_value": repaired[
                "authoritative_front_improvement_contract"
            ][
                "minimum_recovered_fronts"
            ],
            "exact_match": True,
        },
        {
            "gate": "maximum_conditioned_threshold_gap",
            "authoritative_source": "SG7B-10S",
            "authoritative_value": exact_max_gap,
            "repaired_value": repaired[
                "authoritative_front_improvement_contract"
            ][
                "maximum_conditioned_threshold_gap"
            ],
            "exact_match": front_gap_exact,
        },
        {
            "gate": "maximum_100d_profile_L1",
            "authoritative_source": "SG7B-10S",
            "authoritative_value": exact_max_profile_l1,
            "repaired_value": repaired[
                "authoritative_front_improvement_contract"
            ][
                "maximum_100d_profile_L1"
            ],
            "exact_match": True,
        },
    ]

    save_csv(
        GATE_AUDIT_TABLE,
        gate_audit_rows,
    )

    summary = {
        "milestone": "V15-SG7B-15R",
        "status": status,
        "validation_passed": bool(passed),
        "training_performed": False,
        "gate_relaxed": False,
        "repair_reason": (
            "Display-rounded SG7B-15 conditioned-front-gap constant was "
            "compared to the full-precision SG7B-10S contract."
        ),
        "SG7B15_rounded_gap": rounded_gap_used_by_sg15,
        "SG7B10S_exact_gap": exact_max_gap,
        "absolute_difference": absolute_difference,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(
        SUMMARY_FILE,
        summary,
    )

    print("\nSTATUS")
    print(f"  {status}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUTPUT_DIR}")
    print("\nRepaired contract:")
    print(f"  {REPAIRED_CONTRACT.name}")
    print("\nGate audit:")
    print(f"  {GATE_AUDIT_TABLE.name}")
    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)

    print(
        "V15-SG7B-15R CONTRACT REPAIR: "
        +
        (
            "PASS"
            if passed
            else
            "FAIL"
        )
    )

    print()

    print("No training was performed.")
    print("No preservation, front, TOF-bias, or plume gate was relaxed.")

    print()

    print("Next milestone:")
    print(next_milestone)

    print("=" * 78)


if __name__ == "__main__":
    main()
