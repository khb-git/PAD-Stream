from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json
import shutil
import numpy as np


# =============================================================================
# PAD-Stream V15-SG7C-R3F5-R1F3
# Crossing-Local Candidate Freeze / Provenance Manifest
#
# FORMAL FREEZE MILESTONE
#
# NO TRAINING.
# NO MODEL PARAMETERS CHANGED.
# NO L2 GAMMA OR CROSSING GUARD RECALIBRATED.
# NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE CHANGED OR RELAXED.
#
# PURPOSE
# -------
# R1F2C-R established:
#
#   CROSSING_LOCAL_CANDIDATE_FREEZE_READY
#
# and:
#
#   L2_PRECISION_AWARE_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT
#
# R1F3 formally freezes the validated deployment candidate by:
#
#   1. verifying the R1F2C-R freeze-readiness manifest,
#   2. verifying every repaired independent gate is PASS,
#   3. verifying candidate identity = L2,
#   4. verifying X08 support remains unchanged,
#   5. verifying selected crossing guard provenance,
#   6. hashing every authoritative upstream artifact used by the candidate,
#   7. creating immutable freeze copies of the validated numerical candidate,
#   8. generating a complete provenance chain and deployment freeze manifest.
#
# R1F3 DOES NOT ALTER ANY MODEL OR CANDIDATE ARRAY.
# It only copies and hashes the already validated artifacts.
#
# After R1F3, the frozen SG7C candidate is authoritative for the downstream
# map-back / SG7E deployment validation branch.
# =============================================================================


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "V15_SG7CR3F5R1F3"
OUT.mkdir(parents=True, exist_ok=True)

FROZEN_DIR = OUT / "frozen_candidate"
FROZEN_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Authoritative prerequisites
# -----------------------------------------------------------------------------

R1F2CRR_SUMMARY = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "PAD_Stream_V15SG7CR3F5R1F2CRR_Summary.json"
)

R1F2CRR_FREEZE_READY = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Freeze_Readiness_Manifest.json"
)

R1F2CRR_GATES = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Final_Gate_Matrix.csv"
)

R1F2CRR_NUMERICAL = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Independent_Validation.npz"
)

R1F2CRR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CRR"
    / "V15SG7CR3F5R1F2CRR_Repaired_Independent_Validation_Contract.json"
)

R1F2A_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_Crossing_Protection_Contract.json"
)

R1F2A_MATRIX = (
    ROOT / "output" / "V15_SG7CR3F5R1F2A"
    / "V15SG7CR3F5R1F2A_R1F2B_Design_Matrix.csv"
)

R1F2B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1F2B"
    / "V15SG7CR3F5R1F2B_Candidate_Manifest.json"
)

R1F2CR_CONTRACT = (
    ROOT / "output" / "V15_SG7CR3F5R1F2CR"
    / "V15SG7CR3F5R1F2CR_Precision_Aware_Closure_Contract.json"
)

R1B_MANIFEST = (
    ROOT / "output" / "V15_SG7CR3F5R1B"
    / "V15SG7CR3F5R1B_Candidate_Manifest.json"
)

R1A2R4A_IDENTITY = (
    ROOT / "output" / "V15_SG7CR3F5R1A2R4A"
    / "V15SG7CR3F5R1A2R4A_Historical_B4_Identity_Contract.json"
)

# -----------------------------------------------------------------------------
# Outputs
# -----------------------------------------------------------------------------

SUMMARY_FILE = OUT / "PAD_Stream_V15SG7CR3F5R1F3_Summary.json"
PROVENANCE_TABLE = OUT / "V15SG7CR3F5R1F3_Provenance_Chain.csv"
HASH_TABLE = OUT / "V15SG7CR3F5R1F3_Artifact_Hashes.csv"
GATE_TABLE = OUT / "V15SG7CR3F5R1F3_Frozen_Gate_Record.csv"
CANDIDATE_TABLE = OUT / "V15SG7CR3F5R1F3_Frozen_Candidate_Identity.csv"

FREEZE_MANIFEST = OUT / "V15SG7CR3F5R1F3_Freeze_Manifest.json"
DEPLOYMENT_CONTRACT = OUT / "V15SG7CR3F5R1F3_Frozen_Deployment_Contract.json"

FROZEN_NUMERICAL = (
    FROZEN_DIR
    / "V15SG7CR3F5R1F3_L2_Frozen_Deployment_Candidate.npz"
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing prerequisite:\n{path}")
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
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path, chunk_size: int = 1024 * 1024):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def bool_from_csv(value):
    return str(value).strip().lower() in {
        "true", "1", "yes", "pass"
    }


def row_by_experiment(rows, exp):
    for row in rows:
        if row.get("experiment") == exp:
            return row
    return None


# =============================================================================
# Main
# =============================================================================

def main():

    print("\n" + "=" * 78)
    print("PAD-Stream Version 15-SG7C-R3F5-R1F3")
    print("Crossing-Local Candidate Freeze / Provenance Manifest")
    print("=" * 78)

    print("""
FORMAL CANDIDATE FREEZE WILL BE PERFORMED.
NO TRAINING WILL BE PERFORMED.
NO MODEL OR CALIBRATOR PARAMETERS WILL BE CHANGED.
NO L2 GAMMA OR CROSSING-DISTANCE GUARD WILL BE RECALIBRATED.
NO PHYSICS / FRONT / TOF / MAP-BACK / SG7E GATE WILL BE CHANGED OR RELAXED.
THE FREEZE WILL COPY AND HASH THE ALREADY VALIDATED L2 CANDIDATE ONLY.
""")

    # -------------------------------------------------------------------------
    # Load authoritative upstream records.
    # -------------------------------------------------------------------------

    summary = load_json(R1F2CRR_SUMMARY)
    readiness = load_json(R1F2CRR_FREEZE_READY)
    repaired_contract = load_json(R1F2CRR_CONTRACT)
    guard_contract = load_json(R1F2A_CONTRACT)
    l2_matrix = load_csv(R1F2A_MATRIX)
    b_manifest = load_json(R1F2B_MANIFEST)
    precision_contract = load_json(R1F2CR_CONTRACT)
    x08_manifest = load_json(R1B_MANIFEST)
    b4_identity = load_json(R1A2R4A_IDENTITY)
    gate_rows = load_csv(R1F2CRR_GATES)

    # -------------------------------------------------------------------------
    # Freeze-entry validation.
    # -------------------------------------------------------------------------

    checks = []

    checks.append((
        "R1F2C-R freeze-ready status reproduced",
        summary.get("status")
        ==
        "CROSSING_LOCAL_CANDIDATE_FREEZE_READY",
    ))

    checks.append((
        "R1F2C-R diagnosis reproduced",
        summary.get("diagnosis")
        ==
        "L2_PRECISION_AWARE_INDEPENDENT_VALIDATION_PASSES_COMPLETE_CONTRACT",
    ))

    checks.append((
        "Freeze-readiness flag = true",
        bool(readiness.get("freeze_ready", False)),
    ))

    checks.append((
        "Candidate identity = L2",
        readiness.get("candidate") == "L2"
        and
        b_manifest.get("selected_experiment") == "L2",
    ))

    checks.append((
        "Candidate not previously frozen",
        not bool(readiness.get("candidate_frozen", False)),
    ))

    checks.append((
        "No model weights changed upstream",
        not bool(readiness.get("model_weights_changed", False)),
    ))

    checks.append((
        "No physics gate changed upstream",
        not bool(readiness.get("physics_gate_changed", False)),
    ))

    checks.append((
        "Precision-aware reconstruction provenance resolved",
        bool(precision_contract.get("quantization_consistent", False)),
    ))

    authoritative_gate_failures = []

    for row in gate_rows:
        if (
            row.get("semantics") == "DIAGNOSTIC_ONLY"
        ):
            continue

        if not bool_from_csv(row.get("passed")):
            authoritative_gate_failures.append(row.get("gate"))

    checks.append((
        "Every authoritative repaired independent gate passes",
        len(authoritative_gate_failures) == 0,
    ))

    # Candidate support / guard identity.
    exact_support = float(readiness["exact_support_fraction"])
    selected_guard = float(readiness["selected_guard_half_width"])

    checks.append((
        "Exact support remains above unchanged 50% gate",
        exact_support >= 0.50,
    ))

    checks.append((
        "Selected guard matches R1F2A contract",
        abs(
            selected_guard
            -
            float(guard_contract["selected_guard_half_width"])
        )
        <=
        1e-15,
    ))

    # L2 design presence.
    l2_row = row_by_experiment(l2_matrix, "L2")

    checks.append((
        "Persisted L2 design record found",
        l2_row is not None,
    ))

    # B4 historical identity chain.
    selected_b4_sha = (
        b4_identity.get("selected_sha256")
        or
        b4_identity.get("sha256")
        or
        b4_identity.get("selected_identity_sha256")
    )

    checks.append((
        "Historical B4 provenance contract loaded",
        isinstance(b4_identity, dict),
    ))

    # -------------------------------------------------------------------------
    # Numerical freeze copy.
    # -------------------------------------------------------------------------

    if not R1F2CRR_NUMERICAL.exists():
        raise FileNotFoundError(
            f"Missing validated numerical candidate:\n{R1F2CRR_NUMERICAL}"
        )

    # Read before copy and verify expected arrays.
    db = np.load(R1F2CRR_NUMERICAL, allow_pickle=True)

    required_arrays = [
        "xi",
        "tau_end",
        "truth100",
        "frozen100",
        "K5_100",
        "L2_independent_100",
        "L2_gamma_independent",
        "X08_coeff100",
        "exact_support_fraction",
        "truth_front_xi",
        "guard_mask",
        "selected_guard_half_width",
        "gamma_precision_aware_envelope",
        "state_precision_aware_envelope",
    ]

    missing_arrays = [
        key for key in required_arrays
        if key not in db.files
    ]

    checks.append((
        "Validated numerical candidate contains complete freeze arrays",
        len(missing_arrays) == 0,
    ))

    if missing_arrays:
        raise RuntimeError(
            "Cannot freeze incomplete candidate arrays: "
            + ", ".join(missing_arrays)
        )

    numerical_source_sha = sha256(R1F2CRR_NUMERICAL)

    # Copy exactly. Do not reserialize arrays.
    shutil.copy2(
        R1F2CRR_NUMERICAL,
        FROZEN_NUMERICAL,
    )

    numerical_frozen_sha = sha256(FROZEN_NUMERICAL)

    checks.append((
        "Frozen numerical copy SHA-256 matches validated source",
        numerical_source_sha == numerical_frozen_sha,
    ))

    # -------------------------------------------------------------------------
    # Hash provenance artifacts.
    # -------------------------------------------------------------------------

    provenance_artifacts = [
        ("R1F2C-R summary", R1F2CRR_SUMMARY),
        ("R1F2C-R freeze readiness", R1F2CRR_FREEZE_READY),
        ("R1F2C-R gate matrix", R1F2CRR_GATES),
        ("R1F2C-R numerical validation", R1F2CRR_NUMERICAL),
        ("R1F2C-R repaired contract", R1F2CRR_CONTRACT),
        ("R1F2CR precision contract", R1F2CR_CONTRACT),
        ("R1F2A crossing guard contract", R1F2A_CONTRACT),
        ("R1F2A L2 design matrix", R1F2A_MATRIX),
        ("R1F2B nomination manifest", R1F2B_MANIFEST),
        ("R1B X08 candidate manifest", R1B_MANIFEST),
        ("R1A2R4A B4 identity contract", R1A2R4A_IDENTITY),
        ("R1F3 frozen numerical candidate", FROZEN_NUMERICAL),
    ]

    hash_rows = []

    for role, path in provenance_artifacts:
        if not path.exists():
            raise FileNotFoundError(
                f"Missing provenance artifact:\n{path}"
            )

        hash_rows.append({
            "role": role,
            "path": str(path),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })

    save_csv(HASH_TABLE, hash_rows)

    # -------------------------------------------------------------------------
    # Candidate identity record.
    # -------------------------------------------------------------------------

    candidate = np.load(FROZEN_NUMERICAL, allow_pickle=True)

    candidate_state = np.asarray(
        candidate["L2_independent_100"],
        dtype=np.float64,
    )

    candidate_gamma = np.asarray(
        candidate["L2_gamma_independent"],
        dtype=np.float64,
    )

    guard_mask = np.asarray(
        candidate["guard_mask"],
        dtype=np.uint8,
    ).astype(bool)

    candidate_identity_rows = [{
        "candidate": "L2",
        "freeze_milestone": "V15-SG7C-R3F5-R1F3",
        "source_validation_milestone": "V15-SG7C-R3F5-R1F2C-R",
        "frozen_numerical_file": str(FROZEN_NUMERICAL),
        "frozen_numerical_sha256": numerical_frozen_sha,
        "state_shape": "x".join(map(str, candidate_state.shape)),
        "gamma_shape": "x".join(map(str, candidate_gamma.shape)),
        "guard_shape": "x".join(map(str, guard_mask.shape)),
        "candidate_state_min": float(np.min(candidate_state)),
        "candidate_state_max": float(np.max(candidate_state)),
        "candidate_gamma_min": float(np.min(candidate_gamma)),
        "candidate_gamma_max": float(np.max(candidate_gamma)),
        "guard_point_fraction": float(np.mean(guard_mask)),
        "exact_support_fraction": exact_support,
        "selected_guard_half_width": selected_guard,
        "gamma_precision_aware_envelope":
            float(readiness["gamma_precision_aware_envelope"]),
        "state_precision_aware_envelope":
            float(readiness["state_precision_aware_envelope"]),
        "historical_B4_sha256": selected_b4_sha,
    }]

    save_csv(CANDIDATE_TABLE, candidate_identity_rows)

    # -------------------------------------------------------------------------
    # Frozen gate record.
    # -------------------------------------------------------------------------

    frozen_gate_rows = []

    for row in gate_rows:
        frozen_gate_rows.append({
            "candidate": "L2",
            "gate": row.get("gate"),
            "passed": row.get("passed"),
            "semantics": row.get("semantics", "AUTHORITATIVE"),
            "value": row.get("value", ""),
            "source_milestone": "V15-SG7C-R3F5-R1F2C-R",
            "frozen_by": "V15-SG7C-R3F5-R1F3",
        })

    save_csv(GATE_TABLE, frozen_gate_rows)

    # -------------------------------------------------------------------------
    # Provenance chain.
    # -------------------------------------------------------------------------

    provenance_rows = [
        {
            "order": 1,
            "milestone": "V15-SG7CR3F5-R1A2R4A",
            "role": "Historical B4 checkpoint identity resolution",
            "decision": "R3F4 B4 Best-Any is authoritative support source",
        },
        {
            "order": 2,
            "milestone": "V15-SG7CR3F5-R1B",
            "role": "Exact-array support extension",
            "decision": "X08 nominated with support > 50%",
        },
        {
            "order": 3,
            "milestone": "V15-SG7CR3F5-R1C / R1CR",
            "role": "Independent support validation / failure decomposition",
            "decision": "TOF bias pre-existed X08 support extension",
        },
        {
            "order": 4,
            "milestone": "V15-SG7CR3F5-R1D / R1E / R1ER",
            "role": "Joint support / TOF reconciliation",
            "decision": "Front-mask effective-beta capacity limiter",
        },
        {
            "order": 5,
            "milestone": "V15-SG7CR3F5-R1F0 / R1F1 / R1F1R",
            "role": "Non-front correction branch",
            "decision": "Truth-value front mask overprotects safe residual",
        },
        {
            "order": 6,
            "milestone": "V15-SG7CR3F5-R1F2A",
            "role": "Crossing-distance front protection design",
            "decision":
                f"Selected guard half-width {selected_guard:.12e}",
        },
        {
            "order": 7,
            "milestone": "V15-SG7CR3F5-R1F2B",
            "role": "Controlled crossing-local correction",
            "decision": "L2 least-aggressive complete-contract candidate",
        },
        {
            "order": 8,
            "milestone": "V15-SG7CR3F5-R1F2C / R1F2CR / R1F2C-R",
            "role": "Independent validation and precision provenance",
            "decision":
                "L2 passes complete contract under audited precision-aware reconstruction closure",
        },
        {
            "order": 9,
            "milestone": "V15-SG7CR3F5-R1F3",
            "role": "Formal freeze",
            "decision": "L2 frozen as authoritative SG7C deployment candidate",
        },
    ]

    save_csv(PROVENANCE_TABLE, provenance_rows)

    # -------------------------------------------------------------------------
    # Final freeze validation.
    # -------------------------------------------------------------------------

    complete = all(bool(passed) for _, passed in checks)

    print("\n" + "=" * 78)
    print("V15-SG7C-R3F5-R1F3 FREEZE VALIDATION")
    print("=" * 78)

    for desc, passed in checks:
        print(
            f"[{'PASS' if passed else 'FAIL'}] "
            f"{desc}"
        )

    if complete:

        status = "SG7C_CROSSING_LOCAL_CANDIDATE_FROZEN"

        diagnosis = "L2_FROZEN_AS_AUTHORITATIVE_DEPLOYMENT_TRANSPORT_CORRECTION"

        recommendation = (
            "The independently validated L2 candidate is now frozen with a complete "
            "hash-based provenance chain. Treat the frozen R1F3 numerical artifact and "
            "freeze manifest as authoritative for downstream deployment. Do not retrain, "
            "recalibrate, replace the crossing guard, or modify the accepted transport "
            "gates. Proceed to downstream map-back / SG7E validation using the frozen L2 state."
        )

        next_milestone = (
            "V15-SG7D — Frozen L2 Streamline-to-Grid Map-Back Integration"
        )

    else:

        status = "SG7C_FREEZE_BLOCKED"

        diagnosis = "FREEZE_PROVENANCE_VALIDATION_FAILED"

        failed_checks = [
            desc for desc, passed in checks
            if not passed
        ]

        recommendation = (
            "Do not freeze or deploy L2. Repair only the failed provenance/freeze checks; "
            "do not alter the candidate or any physics/front/TOF acceptance gate."
        )

        next_milestone = (
            "V15-SG7C-R3F5-R1F3R — Freeze Provenance Repair"
        )

    # -------------------------------------------------------------------------
    # Manifest and deployment contract.
    # -------------------------------------------------------------------------

    freeze_payload = {
        "milestone": "V15-SG7C-R3F5-R1F3",
        "status": status,
        "diagnosis": diagnosis,
        "candidate": "L2",
        "candidate_frozen": complete,
        "freeze_ready_source": "V15-SG7C-R3F5-R1F2C-R",
        "frozen_numerical_file": str(FROZEN_NUMERICAL),
        "frozen_numerical_sha256": numerical_frozen_sha,
        "source_numerical_sha256": numerical_source_sha,
        "exact_support_fraction": exact_support,
        "selected_guard_half_width": selected_guard,
        "gamma_precision_aware_envelope":
            float(readiness["gamma_precision_aware_envelope"]),
        "state_precision_aware_envelope":
            float(readiness["state_precision_aware_envelope"]),
        "all_authoritative_gates_pass":
            len(authoritative_gate_failures) == 0,
        "authoritative_gate_failures":
            authoritative_gate_failures,
        "model_weights_changed": False,
        "candidate_arrays_changed": False,
        "gate_changed": False,
        "recommendation": recommendation,
        "next_milestone": next_milestone,
    }

    save_json(FREEZE_MANIFEST, freeze_payload)

    deployment_contract = {
        "contract_name":
            "PAD-Stream V15-SG7C Frozen L2 Deployment Transport Contract",

        "freeze_milestone":
            "V15-SG7C-R3F5-R1F3",

        "candidate":
            "L2",

        "candidate_status":
            status,

        "authoritative_numerical_artifact":
            str(FROZEN_NUMERICAL),

        "authoritative_sha256":
            numerical_frozen_sha,

        "transport_model":
            "Frozen SG7B-11 PI-RNN plus frozen deployment-side correction chain",

        "support_candidate":
            "X08",

        "crossing_local_candidate":
            "L2",

        "physics_front_reference":
            "SG7A / canonical truth",

        "frozen_model_reference":
            "SG7B-11 regression diagnostic",

        "front_protection":
            {
                "type": "crossing-distance guard",
                "threshold": 0.21,
                "half_width": selected_guard,
                "candidate": "L2",
            },

        "precision_closure":
            {
                "basis":
                    "R1F2CR persisted float32 ULP provenance",
                "gamma_envelope":
                    float(readiness["gamma_precision_aware_envelope"]),
                "state_envelope":
                    float(readiness["state_precision_aware_envelope"]),
            },

        "invariants":
            {
                "SG7B11_weights_immutable": True,
                "B4_checkpoint_immutable": True,
                "X08_support_geometry_immutable": True,
                "L2_gamma_immutable": True,
                "crossing_guard_immutable": True,
                "physics_gates_immutable": True,
                "TOF_gates_immutable": True,
            },

        "downstream_use":
            "Use frozen L2 state for streamline-to-grid map-back and SG7E validation.",

        "next_milestone":
            next_milestone,
    }

    save_json(DEPLOYMENT_CONTRACT, deployment_contract)

    save_json(
        SUMMARY_FILE,
        {
            "milestone": "V15-SG7C-R3F5-R1F3",
            "status": status,
            "diagnosis": diagnosis,
            "candidate": "L2",
            "candidate_frozen": complete,
            "frozen_numerical_sha256": numerical_frozen_sha,
            "exact_support_fraction": exact_support,
            "selected_guard_half_width": selected_guard,
            "training_performed": False,
            "model_weights_changed": False,
            "candidate_arrays_changed": False,
            "gate_changed": False,
            "recommendation": recommendation,
            "next_milestone": next_milestone,
        },
    )

    # -------------------------------------------------------------------------
    # Console summary.
    # -------------------------------------------------------------------------

    print("=" * 78)

    print("\nFROZEN CANDIDATE")
    print("  Candidate               : L2")
    print(
        f"  Exact support           : "
        f"{100*exact_support:.6f}%"
    )
    print(
        f"  Crossing guard half-width: "
        f"{selected_guard:.12e}"
    )
    print(
        f"  Frozen artifact         : "
        f"{FROZEN_NUMERICAL.name}"
    )
    print(
        f"  SHA-256                 : "
        f"{numerical_frozen_sha}"
    )
    print(
        f"  Source/frozen hash match: "
        f"{numerical_source_sha == numerical_frozen_sha}"
    )

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

    print("\nFrozen candidate:")
    print(f"  {FROZEN_NUMERICAL}")

    print("\nTables:")
    print(f"  {PROVENANCE_TABLE.name}")
    print(f"  {HASH_TABLE.name}")
    print(f"  {GATE_TABLE.name}")
    print(f"  {CANDIDATE_TABLE.name}")

    print("\nFreeze manifest:")
    print(f"  {FREEZE_MANIFEST.name}")

    print("\nFrozen deployment contract:")
    print(f"  {DEPLOYMENT_CONTRACT.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_FILE.name}")

    print("\n" + "=" * 78)

    if complete:
        print("V15-SG7C-R3F5-R1F3 FORMAL FREEZE: PASS")
        print()
        print("L2 is now frozen as the authoritative SG7C deployment candidate.")
        print("No training was performed.")
        print("No candidate array was changed.")
        print("No gate was changed or relaxed.")
        print()
        print("Next milestone:")
        print(next_milestone)

    else:
        print("V15-SG7C-R3F5-R1F3 FORMAL FREEZE: BLOCKED")
        print()
        print("No candidate was frozen.")
        print("No gate was changed or relaxed.")
        print()
        print("Next milestone:")
        print(next_milestone)

    print("=" * 78)


if __name__ == "__main__":
    main()
