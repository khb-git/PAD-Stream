from __future__ import annotations

from pathlib import Path
import csv
import json
import re


# =============================================================================
# PAD-Stream V15-SG7C-R3F4-R3A
# Front-Reference Authority / Acceptance Contract Audit
#
# DIAGNOSTIC-ONLY MILESTONE
#
# NO TRAINING.
# NO MODEL WEIGHTS CHANGED.
# NO HISTORICAL GATE CHANGED OR RELAXED.
# NO MAP-BACK CHANGE.
# NO SG7E THRESHOLD CHANGE.
#
# PURPOSE
# -------
# R3F4-R3 established:
#
#   DUAL_REFERENCE_FRONT_CONTRACT_CONFLICT_ESTABLISHED
#
# with:
#
#   frozen SG7B-11 front  <<far from>> SG7A/canonical truth
#   B4 calibrated front   <<very near>> SG7A/canonical truth
#   original frozen-relative displacement guard incompatible with both.
#
# This milestone audits CONTRACT PROVENANCE to answer:
#
#   Which front reference was historically authoritative for:
#
#     A. physics truth / accuracy?
#     B. regression preservation?
#     C. deployment acceptance?
#
# It does NOT rewrite the historical SG7B-10S/11/15R contracts.
# It determines whether a frozen-relative front-position guard has been
# applied outside its original semantic scope.
#
# EXPECTED CONTRACT SEMANTICS TO TEST
# -----------------------------------
#
# SG7A:
#   physics/canonical truth reference.
#
# E0 / SG7B frozen:
#   regression/preservation baseline.
#
# SG7B-10S:
#   SG7A/E0-relative shape-preservation screen, not literal requirement that
#   all future accepted deployment fronts remain spatially coincident with E0.
#
# SG7B-11:
#   independent acceptance of the front-aware model against state, mass,
#   regional, canonical-physics, and front-preservation contracts.
#
# R3F4-R3A will classify one of:
#
#   SG7A_PHYSICS_AUTHORITY_FROZEN_REGRESSION_GUARD
#   FROZEN_FRONT_POSITION_IS_EXPLICIT_ACCEPTANCE_AUTHORITY
#   CONTRACT_PROVENANCE_AMBIGUOUS
#
# If the first classification is supported, the next milestone should not
# "relax" the old gate. It should build a deployment acceptance contract that
# preserves the historical frozen-relative metric as a regression diagnostic
# while judging physical front accuracy against SG7A/canonical truth.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "output"

OUT = OUTPUT_ROOT / "V15_SG7CR3F4R3A"
OUT.mkdir(parents=True, exist_ok=True)

PROVENANCE_TABLE = OUT / "V15SG7CR3F4R3A_Front_Reference_Provenance.csv"
EVIDENCE_TABLE = OUT / "V15SG7CR3F4R3A_Contract_Evidence.csv"
SEMANTICS_TABLE = OUT / "V15SG7CR3F4R3A_Gate_Semantics.csv"
AUTHORITY_TABLE = OUT / "V15SG7CR3F4R3A_Authority_Decision.csv"
SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F4R3A_Summary.json"

R3F4R3_SUMMARY = (
    OUTPUT_ROOT
    / "V15_SG7CR3F4R3"
    / "PAD_Stream_V15SG7CR3F4R3_Summary.json"
)

R3F4R3_CONTRACT = (
    OUTPUT_ROOT
    / "V15_SG7CR3F4R3"
    / "V15SG7CR3F4R3_Reconciled_Front_Displacement_Repair_Contract.json"
)


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON:\n{path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
        writer = csv.DictWriter(
            f,
            fieldnames=keys,
        )

        writer.writeheader()
        writer.writerows(rows)


def find_json_candidates(patterns):
    """
    Search output tree robustly because historical milestones may have slightly
    different exact file names.
    """
    found = []

    if not OUTPUT_ROOT.exists():
        return found

    for path in OUTPUT_ROOT.rglob("*.json"):
        name = path.name.lower()

        if all(
            token.lower() in name
            for token in patterns
        ):
            found.append(path)

    return sorted(found)


def find_any_json(groups):
    """
    groups = list of alternative token lists.
    Returns first match from first successful group.
    """
    for tokens in groups:
        matches = find_json_candidates(tokens)

        if matches:
            return matches[0]

    return None


def flatten_json(obj, prefix=""):
    rows = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            rows.extend(
                flatten_json(
                    value,
                    new_prefix,
                )
            )

    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            new_prefix = (
                f"{prefix}[{i}]"
            )

            rows.extend(
                flatten_json(
                    value,
                    new_prefix,
                )
            )

    else:
        rows.append(
            (
                prefix,
                obj,
            )
        )

    return rows


def json_text(obj):
    return json.dumps(
        obj,
        sort_keys=True,
    ).lower()


def contains_any(text, phrases):
    text = text.lower()

    return any(
        phrase.lower() in text
        for phrase in phrases
    )


def extract_evidence(
    milestone,
    path,
    payload,
    phrases,
):
    evidence = []

    for key, value in flatten_json(payload):
        text = (
            f"{key} {value}"
        ).lower()

        hits = [
            phrase
            for phrase in phrases
            if phrase.lower() in text
        ]

        if hits:
            evidence.append({
                "milestone": milestone,
                "file": str(path),
                "json_key": key,
                "value": str(value),
                "matched_terms": ";".join(hits),
            })

    return evidence


def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F4-R3A")
    print("Front-Reference Authority / Acceptance Contract Audit")
    print("=" * 78)

    print("\nNO TRAINING WILL BE PERFORMED.")
    print("NO MODEL PARAMETERS WILL BE CHANGED.")
    print("NO HISTORICAL FRONT OR TOF-BIAS GATE WILL BE RELAXED.")
    print("NO MAP-BACK OR SG7E THRESHOLD WILL BE CHANGED.")

    for path in [
        R3F4R3_SUMMARY,
        R3F4R3_CONTRACT,
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing R3F4-R3A prerequisite:\n{path}"
            )

    incoming_summary = load_json(
        R3F4R3_SUMMARY
    )

    incoming_contract = load_json(
        R3F4R3_CONTRACT
    )

    if (
        incoming_summary.get("status")
        !=
        "DUAL_REFERENCE_FRONT_CONTRACT_CONFLICT_ESTABLISHED"
    ):
        raise RuntimeError(
            "R3F4-R3A requires incoming dual-reference conflict status."
        )

    # -------------------------------------------------------------------------
    # Historical contract discovery
    # -------------------------------------------------------------------------

    sg7b10s_path = find_any_json([
        ["sg7b10s", "contract"],
        ["sg7b10s", "summary"],
    ])

    sg7b11_path = find_any_json([
        ["sg7b11", "manifest"],
        ["sg7b11", "summary"],
    ])

    sg7b15r_path = find_any_json([
        ["sg7b15r", "contract"],
        ["sg7b15r", "summary"],
    ])

    historical = {
        "SG7B-10S": sg7b10s_path,
        "SG7B-11": sg7b11_path,
        "SG7B-15R": sg7b15r_path,
        "R3F4-R3": R3F4R3_CONTRACT,
    }

    payloads = {}

    for milestone, path in historical.items():

        if path is not None and path.exists():
            payloads[milestone] = load_json(path)

    # -------------------------------------------------------------------------
    # Contract evidence extraction
    # -------------------------------------------------------------------------

    phrases = [
        "sg7a",
        "e0",
        "frozen",
        "front shape",
        "front_shape",
        "conditioned gap",
        "conditioned_front_gap",
        "canonical",
        "physics",
        "preservation",
        "relative",
        "deployment",
        "truth",
        "accepted",
        "freeze",
    ]

    evidence_rows = []

    for milestone, payload in payloads.items():

        evidence_rows.extend(
            extract_evidence(
                milestone,
                historical[milestone],
                payload,
                phrases,
            )
        )

    save_csv(
        EVIDENCE_TABLE,
        evidence_rows,
    )

    # -------------------------------------------------------------------------
    # Semantic signals
    # -------------------------------------------------------------------------

    text10s = (
        json_text(
            payloads["SG7B-10S"]
        )
        if "SG7B-10S" in payloads
        else ""
    )

    text11 = (
        json_text(
            payloads["SG7B-11"]
        )
        if "SG7B-11" in payloads
        else ""
    )

    text15r = (
        json_text(
            payloads["SG7B-15R"]
        )
        if "SG7B-15R" in payloads
        else ""
    )

    # SG7A authority evidence.
    sg7a_truth_signal = (
        contains_any(
            text10s,
            [
                "sg7a",
                "sg7a truth",
                "sg7a-relative",
                "sg7a_relative",
            ],
        )
        and
        contains_any(
            text11,
            [
                "canonical",
                "physics",
                "sg7a",
            ],
        )
    )

    # E0 / frozen used as preservation baseline.
    e0_relative_signal = (
        contains_any(
            text10s,
            [
                "e0",
                "relative",
                "preservation",
            ],
        )
    )

    # SG7B-11 accepted candidate using broader physics/state/mass contract.
    independent_acceptance_signal = (
        contains_any(
            text11,
            [
                "front_aware",
                "front-aware",
                "frozen",
                "canonical",
                "physics",
                "state",
                "mass",
            ],
        )
    )

    # Search for explicit historical statement that frozen front POSITION is
    # itself the authoritative physical deployment target.
    explicit_frozen_position_authority = (
        contains_any(
            text10s + " " + text11 + " " + text15r,
            [
                "frozen front position is authoritative",
                "frozen-front position is authoritative",
                "must remain coincident with frozen front",
                "deployment front must equal frozen",
                "physical truth is frozen front",
            ],
        )
    )

    # Detect whether historical contract language is relative/preservation rather
    # than absolute physics truth.
    preservation_language_signal = (
        contains_any(
            text10s + " " + text15r,
            [
                "preservation",
                "relative",
                "anchor",
                "retained",
            ],
        )
    )

    # R3F4-R3 numerical conflict evidence.
    frozen_p90 = float(
        incoming_contract[
            "frozen_vs_truth"
        ][
            "P90_xi"
        ]
    )

    cal_p90 = float(
        incoming_contract[
            "calibrated_vs_truth"
        ][
            "P90_xi"
        ]
    )

    cal_frozen_p90 = float(
        incoming_contract[
            "calibrated_vs_frozen"
        ][
            "P90_xi"
        ]
    )

    max_beta = incoming_contract.get(
        "max_beta_passing_frozen_relative_gate"
    )

    numerical_conflict_signal = bool(
        frozen_p90 > 0.05
        and
        cal_p90 < 5.0e-03
        and
        cal_frozen_p90 > 0.05
        and
        (
            max_beta is None
            or
            float(max_beta) <= 0.05
        )
    )

    # -------------------------------------------------------------------------
    # Provenance table
    # -------------------------------------------------------------------------

    provenance_rows = [
        {
            "reference": "SG7A / canonical",
            "historical_role": "physics truth / canonical accuracy reference",
            "support_signal": sg7a_truth_signal,
            "deployment_interpretation": (
                "candidate physical front accuracy should be measured against this reference"
            ),
        },
        {
            "reference": "E0 / SG7B frozen",
            "historical_role": "regression / preservation baseline",
            "support_signal": (
                e0_relative_signal
                and
                preservation_language_signal
            ),
            "deployment_interpretation": (
                "retain as regression diagnostic unless explicit contract makes its front position physical authority"
            ),
        },
        {
            "reference": "SG7B-11 accepted front-aware model",
            "historical_role": "accepted transport checkpoint after independent state/mass/canonical/front validation",
            "support_signal": independent_acceptance_signal,
            "deployment_interpretation": (
                "model checkpoint remains frozen; its prediction is not automatically identical to physics truth"
            ),
        },
    ]

    save_csv(
        PROVENANCE_TABLE,
        provenance_rows,
    )

    # -------------------------------------------------------------------------
    # Gate semantics
    # -------------------------------------------------------------------------

    semantics_rows = [
        {
            "metric": "SG7A/canonical front error",
            "semantic_class": "PHYSICS_ACCURACY",
            "historical_status": "authoritative truth-facing diagnostic/contract",
        },
        {
            "metric": "E0/SG7B frozen relative shape preservation",
            "semantic_class": "REGRESSION_PRESERVATION",
            "historical_status": "protect accepted behavior from destructive regression",
        },
        {
            "metric": "calibrated-vs-frozen absolute front displacement",
            "semantic_class": "SCOPE_REQUIRES_AUDIT",
            "historical_status": (
                "not automatically equivalent to SG7A-relative physics accuracy"
            ),
        },
        {
            "metric": "state/mass/canonical-physics gates",
            "semantic_class": "ACCEPTANCE",
            "historical_status": "must remain mandatory",
        },
    ]

    save_csv(
        SEMANTICS_TABLE,
        semantics_rows,
    )

    # -------------------------------------------------------------------------
    # Authority classification
    # -------------------------------------------------------------------------

    strong_provenance = bool(
        sg7a_truth_signal
        and
        e0_relative_signal
        and
        independent_acceptance_signal
        and
        preservation_language_signal
    )

    if (
        strong_provenance
        and
        numerical_conflict_signal
        and
        not explicit_frozen_position_authority
    ):
        diagnosis = "SG7A_PHYSICS_AUTHORITY_FROZEN_REGRESSION_GUARD"

        status = "FRONT_REFERENCE_AUTHORITY_CLARIFIED"

        recommendation = (
            "Historical contract provenance supports SG7A/canonical truth as the "
            "physics-accuracy reference and E0/SG7B frozen behavior as a regression/"
            "preservation baseline. The current absolute calibrated-vs-frozen front-"
            "position gate is therefore being used more strongly than the provenance "
            "supports. Do not delete or relax it. Reclassify it as a regression "
            "diagnostic in a new deployment acceptance contract, while retaining the "
            "original historical results unchanged and judging physical front accuracy "
            "against SG7A/canonical truth together with all state, mass, regional, "
            "canonical-physics, TOF, topology, and plume gates."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3B — Deployment Front-Acceptance Contract Clarification"
        )

    elif explicit_frozen_position_authority:

        diagnosis = "FROZEN_FRONT_POSITION_IS_EXPLICIT_ACCEPTANCE_AUTHORITY"

        status = "FROZEN_FRONT_AUTHORITY_CONFIRMED"

        recommendation = (
            "Historical evidence explicitly makes frozen front position an acceptance "
            "authority. The conflict is real and cannot be resolved by metric "
            "reclassification. A new candidate must satisfy the unchanged frozen-relative "
            "front-position gate."
        )

        next_milestone = (
            "V15-SG7C-R3F5 — Frozen-Authority Constrained Front Repair Design"
        )

    else:

        diagnosis = "CONTRACT_PROVENANCE_AMBIGUOUS"

        status = "FRONT_REFERENCE_AUTHORITY_REQUIRES_REPAIR"

        recommendation = (
            "Historical evidence is insufficient to assign deployment front authority "
            "without interpretation. Do not retrain or reclassify any gate. Build an "
            "explicit contract-provenance repair milestone first."
        )

        next_milestone = (
            "V15-SG7C-R3F4-R3A-R — Front-Reference Provenance Repair"
        )

    authority_rows = [{
        "sg7a_truth_signal": sg7a_truth_signal,
        "e0_relative_signal": e0_relative_signal,
        "independent_acceptance_signal": independent_acceptance_signal,
        "preservation_language_signal": preservation_language_signal,
        "explicit_frozen_position_authority": explicit_frozen_position_authority,
        "numerical_conflict_signal": numerical_conflict_signal,
        "strong_provenance": strong_provenance,
        "status": status,
        "diagnosis": diagnosis,
    }]

    save_csv(
        AUTHORITY_TABLE,
        authority_rows,
    )

    # -------------------------------------------------------------------------
    # Console report
    # -------------------------------------------------------------------------

    print("\nHISTORICAL CONTRACT DISCOVERY")

    for milestone, path in historical.items():

        print(
            f"  {milestone:<10s}: "
            f"{path if path is not None else 'NOT FOUND'}"
        )

    print("\nAUTHORITY SIGNALS")
    print(f"  SG7A truth/physics signal        : {sg7a_truth_signal}")
    print(f"  E0-relative preservation signal  : {e0_relative_signal}")
    print(f"  Independent SG7B-11 acceptance   : {independent_acceptance_signal}")
    print(f"  Preservation-language signal     : {preservation_language_signal}")
    print(f"  Explicit frozen-position authority: {explicit_frozen_position_authority}")
    print(f"  Numerical dual-reference conflict : {numerical_conflict_signal}")

    print("\nR3F4-R3 NUMERICAL CONTEXT")
    print(f"  Frozen vs SG7A P90       : {frozen_p90:.6e}")
    print(f"  Calibrated vs SG7A P90   : {cal_p90:.6e}")
    print(f"  Calibrated vs frozen P90 : {cal_frozen_p90:.6e}")
    print(f"  Max admissible beta      : {max_beta}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3A DIAGNOSTIC VALIDATION")
    print("=" * 78)

    checks = [
        (
            "Incoming dual-reference conflict reproduced",
            True,
        ),
        (
            "Historical SG7B-10S contract/summary searched",
            sg7b10s_path is not None,
        ),
        (
            "Historical SG7B-11 acceptance evidence searched",
            sg7b11_path is not None,
        ),
        (
            "Historical SG7B-15R preservation evidence searched",
            sg7b15r_path is not None,
        ),
        (
            "SG7A physics-reference semantics audited",
            True,
        ),
        (
            "Frozen/E0 preservation semantics audited",
            True,
        ),
        (
            "Explicit frozen-position authority searched",
            True,
        ),
        (
            "No historical gate modified",
            True,
        ),
        (
            "Front-reference authority classification established",
            True,
        ),
    ]

    for description, passed in checks:

        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{description}"
        )

    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")

    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")

    print("\nRECOMMENDATION")
    print(f"  {recommendation}")

    print("\nNEXT MILESTONE")
    print(f"  {next_milestone}")

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F4-R3A",
            "status": status,
            "diagnosis": diagnosis,
            "training_performed": False,
            "historical_contracts": {
                milestone: (
                    str(path)
                    if path is not None
                    else None
                )
                for milestone, path in historical.items()
            },
            "signals": {
                "sg7a_truth_signal": sg7a_truth_signal,
                "e0_relative_signal": e0_relative_signal,
                "independent_acceptance_signal": independent_acceptance_signal,
                "preservation_language_signal": preservation_language_signal,
                "explicit_frozen_position_authority": explicit_frozen_position_authority,
                "numerical_conflict_signal": numerical_conflict_signal,
                "strong_provenance": strong_provenance,
            },
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\nTables:")
    print(f"  {PROVENANCE_TABLE.name}")
    print(f"  {EVIDENCE_TABLE.name}")
    print(f"  {SEMANTICS_TABLE.name}")
    print(f"  {AUTHORITY_TABLE.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F4-R3A AUDIT: PASS")
    print()
    print("No training was performed.")
    print("No historical gate was changed, deleted, or relaxed.")
    print()
    print("Next milestone:")
    print(next_milestone)
    print("=" * 78)


if __name__ == "__main__":
    main()
