#!/usr/bin/env python3
"""
PAD-Stream V16E-0A
Legacy BL / DP Model-Artifact Discovery and Provenance Inventory

Purpose
-------
Read-only discovery milestone required before BL/DP adapter coding.

This script scans the local PAD-Stream project for legacy Buckley-Leverett,
PI-RNN, Dykstra-Parsons, Hybrid, and checkpoint artifacts. It computes exact
SHA-256 identities and classifies candidates from source fingerprints.

IMPORTANT
---------
E0A DISCOVERY DOES NOT:
  * import TensorFlow,
  * load any model/checkpoint,
  * open NPZ training/test arrays,
  * train,
  * run inference,
  * reopen geology0029,
  * modify EXP-CS1,
  * assign ambiguous files to BL Round 1/2/3 by guess,
  * authorize adapter coding.

A later V16E-0B binding step may bind exact roles only after this inventory
contains sufficient unambiguous evidence.
"""

from pathlib import Path
import hashlib
import json
import os
import re
import sys


# =============================================================================
# ROOT / OUTPUT
# =============================================================================

R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E0A_LEGACY_BL_DP_MODEL_ARTIFACT_DISCOVERY_INVENTORY"
)
OUT.mkdir(parents=True, exist_ok=True)

INVENTORY = OUT / "V16E0A_Legacy_BL_DP_Artifact_Inventory.json"
CANDIDATE_CSV = OUT / "V16E0A_Legacy_BL_DP_Candidates.csv"
ROLE_REPORT = OUT / "V16E0A_Legacy_Role_Binding_Readiness.json"
SUMMARY = OUT / "PAD_Stream_V16E0A_Summary.json"


# =============================================================================
# E0 AUTHORITY
# =============================================================================

E0_DIR = R / "output" / "V16_E0_BL_DP_ARCHITECTURE_RECONCILIATION_CONTRACT"

E0_CONTRACT = E0_DIR / "V16E0_BL_DP_Architecture_Reconciliation_Contract.json"
E0_INTERFACE = E0_DIR / "V16E0_Common_Transport_Interface.json"
E0_EVIDENCE = E0_DIR / "V16E0_BL_DP_Evidence_and_Role_Map.md"
E0_SUMMARY = E0_DIR / "PAD_Stream_V16E0_Summary.json"

E0_CONTRACT_SHA = "423c5a0b76f3b6724923376fbd7ac1bb469e8dff4b27aede8b5b6c03f204fa47"
E0_INTERFACE_SHA = "12050e303e9076e34a5a66198e25719007f88bbe4254d3b565f9b8b54cbb147e"
E0_EVIDENCE_SHA = "ae3c5d9fde2311ba29b7b0caecec49d7b0264dc052a5399dc5ea9a9c6f5cf3f2"
E0_SUMMARY_SHA = "65adfdaab6ddaf16a17453071637bd0baf19687db965ff96a8497f62ef225a96"

EXPECTED_E0_STATUS = (
    "V16E_BL_DP_ARCHITECTURE_RECONCILIATION_CONTRACT_FROZEN_"
    "COMMON_TOF_INTERFACE_APPROVED_LEGACY_MODEL_INVENTORY_BINDING_AUTHORIZED_"
    "ADAPTER_CODING_NOT_YET_AUTHORIZED"
)


# =============================================================================
# DISCOVERY POLICY
# =============================================================================

# Current project only by default. This keeps discovery deterministic and avoids
# silently scanning unrelated user directories. If legacy files are elsewhere,
# their exact paths can be copied into/pointed at from a later recovery step.
SEARCH_ROOTS = [R]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ipynb_checkpoints",
    "node_modules",
}

# We inspect text/code and list model/checkpoint artifacts. We do not deserialize.
TEXT_SUFFIXES = {
    ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"
}

CHECKPOINT_SUFFIXES = {
    ".keras", ".h5", ".hdf5", ".ckpt", ".index"
}

# Binary checkpoint shards may end in .data-00000-of-00001.
CHECKPOINT_NAME_PATTERNS = [
    re.compile(r".*\.weights\.h5$", re.I),
    re.compile(r".*\.keras$", re.I),
    re.compile(r".*\.h5$", re.I),
    re.compile(r".*\.hdf5$", re.I),
    re.compile(r".*\.ckpt$", re.I),
    re.compile(r".*\.index$", re.I),
    re.compile(r".*\.data-\d+-of-\d+$", re.I),
]

# Avoid hashing enormous unrelated data files.
MAX_TEXT_BYTES = 25 * 1024 * 1024
MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024 * 1024

# Candidate keyword gate. A source need only match one high-value phrase.
HIGH_VALUE_TERMS = [
    "buckley",
    "leverett",
    "pirnn",
    "pi-rnn",
    "pi_rnn",
    "dykstra",
    "parsons",
    "capillary",
    "compressible",
    "fractional flow",
    "fractional_flow",
    "godunov",
    "welge",
    "corey",
    "brooks-corey",
    "brooks_corey",
]


# =============================================================================
# ROLE FINGERPRINTS
# =============================================================================

FINGERPRINTS = {
    "BL_ANALYTICAL_TEACHER": {
        "any": [
            "welge",
            "shock saturation",
            "shock_saturation",
            "fractional flow",
            "fractional_flow",
        ],
        "bonus": [
            "tangent",
            "dfw",
            "shock speed",
            "breakthrough",
        ],
    },

    "BL_FV_INCOMPRESSIBLE": {
        "any": [
            "godunov",
            "finite volume",
            "finite-volume",
            "upwind",
        ],
        "bonus": [
            "incompressible",
            "buckley",
            "fractional_flow",
        ],
    },

    "BL_FV_COMPRESSIBLE": {
        "any": [
            "compressible",
            "compressibility",
            "rho_ref",
            "density(",
        ],
        "bonus": [
            "godunov",
            "finite-volume",
            "finite volume",
            "accumulation",
        ],
    },

    "BL_FV_CAPILLARY": {
        "any": [
            "capillary",
            "solve_banded",
            "implicit diffusion",
            "diffusion",
        ],
        "bonus": [
            "godunov",
            "pe_c",
            "lambda_bc",
            "brooks-corey",
        ],
    },

    "BL_FV_FULL_COMPRESSIBLE_CAPILLARY": {
        "all_groups": [
            ["compressible", "compressibility"],
            ["capillary", "diffusion"],
        ],
        "bonus": [
            "full",
            "godunov",
            "solve_banded",
            "rho",
        ],
    },

    "BL_PI_RNN": {
        "all_groups": [
            ["tensorflow", "keras"],
            ["lstm", "gru", "rnn"],
        ],
        "bonus": [
            "physics loss",
            "physics_loss",
            "lambda_phys",
            "pirnn",
            "pi-rnn",
            "film",
            "fourier",
        ],
    },

    "BL_PI_RNN_CAPILLARY": {
        "all_groups": [
            ["tensorflow", "keras"],
            ["capillary", "pe_c", "lambda_bc"],
            ["lstm", "gru", "rnn"],
        ],
        "bonus": [
            "physics loss",
            "finite-volume capillary",
            "implicit",
            "film",
        ],
    },

    "BL_PI_RNN_COMPRESSIBLE": {
        "all_groups": [
            ["tensorflow", "keras"],
            ["compressible", "compressibility"],
            ["lstm", "gru", "rnn"],
        ],
        "bonus": [
            "physics loss",
            "rho",
            "accumulation",
            "lambda_phys",
        ],
    },

    "BL_PI_RNN_FULL": {
        "all_groups": [
            ["tensorflow", "keras"],
            ["compressible", "compressibility"],
            ["capillary", "diffusion"],
            ["lstm", "gru", "rnn"],
        ],
        "bonus": [
            "physics loss",
            "film",
            "fourier",
            "residual",
        ],
    },

    "DP_8_LAYER_BENCHMARK": {
        "all_groups": [
            ["dykstra", "parsons"],
            ["8-layer", "8 layer", "nz = 8", "nz=8"],
        ],
        "bonus": [
            "layer rate",
            "rate fraction",
            "pore volume",
            "local pvi",
            "flux-weighted",
            "no crossflow",
            "kh",
        ],
    },

    "HYBRID_DP_PI_RNN": {
        "all_groups": [
            ["tensorflow", "keras"],
            ["dykstra", "parsons", "heterogeneity"],
            ["lstm", "gru", "rnn"],
        ],
        "bonus": [
            "hybrid",
            "layer",
            "rate fraction",
            "pore volume",
            "lorenz",
            "f-phi",
            "f_phi",
        ],
    },

    "F_PHI_LORENZ": {
        "any": [
            "f-phi",
            "f_phi",
            "flow-storage",
            "flow_storage",
            "lorenz",
        ],
        "bonus": [
            "tof",
            "flux",
            "storage capacity",
            "flow capacity",
        ],
    },
}


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def valid_sha256_literal(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value.lower())
    )


def read_json(path: Path):
    return json.loads(path.read_text())


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def looks_like_checkpoint(path: Path) -> bool:
    name = path.name
    return (
        path.suffix.lower() in CHECKPOINT_SUFFIXES
        or any(pat.fullmatch(name) for pat in CHECKPOINT_NAME_PATTERNS)
    )


def safe_text(path: Path):
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None, "TEXT_TOO_LARGE"
        raw = path.read_bytes()
        # tolerate mixed encodings without OCR or transformations
        text = raw.decode("utf-8", errors="replace")
        return text, None
    except Exception as exc:
        return None, f"READ_ERROR:{type(exc).__name__}"


def candidate_text_gate(path: Path, text_lower: str) -> bool:
    filename_lower = path.name.lower()
    return any(term in filename_lower or term in text_lower for term in HIGH_VALUE_TERMS)


def role_score(text_lower: str, spec: dict):
    score = 0
    evidence = []

    for term in spec.get("any", []):
        if term in text_lower:
            score += 2
            evidence.append(term)

    all_groups = spec.get("all_groups", [])
    groups_pass = True
    for group in all_groups:
        hits = [term for term in group if term in text_lower]
        if hits:
            score += 3
            evidence.extend(hits[:2])
        else:
            groups_pass = False

    for term in spec.get("bonus", []):
        if term in text_lower:
            score += 1
            evidence.append(term)

    # Roles with required groups are invalid if one group is missing.
    if all_groups and not groups_pass:
        return 0, []

    return score, sorted(set(evidence))


def extract_metadata(text: str):
    low = text.lower()

    metadata = {
        "tensorflow_present": "tensorflow" in low or "tf.keras" in low,
        "lstm_present": "lstm" in low,
        "gru_present": "gru" in low,
        "film_present": "film" in low,
        "fourier_present": "fourier" in low,
        "physics_loss_present":
            "physics loss" in low or "physics_loss" in low or "lambda_phys" in low,
        "checkpoint_save_reference":
            any(x in low for x in [
                "modelcheckpoint",
                "save_weights",
                ".weights.h5",
                ".keras",
                "save(",
            ]),
        "godunov_present": "godunov" in low,
        "capillary_present": "capillary" in low,
        "compressible_present":
            "compressible" in low or "compressibility" in low,
        "dykstra_parsons_present":
            "dykstra" in low and "parsons" in low,
        "eight_layer_present":
            any(x in low for x in ["8-layer", "8 layer", "nz = 8", "nz=8"]),
        "tof_present":
            "time of flight" in low or "time-of-flight" in low or "tof" in low,
        "pollock_present": "pollock" in low,
        "lorenz_present": "lorenz" in low,
    }

    # Capture explicit likely titles near the top, but never infer a round number.
    head = "\n".join(text.splitlines()[:80])
    metadata["head_excerpt"] = head[:3000]

    return metadata


def discover_sources():
    rows = []

    for root in SEARCH_ROOTS:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or is_excluded(path):
                continue

            # Never inventory our generated output copies as legacy candidates.
            try:
                relative = path.relative_to(R)
                if relative.parts and relative.parts[0] == "output":
                    continue
            except ValueError:
                pass

            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue

            text, err = safe_text(path)
            if text is None:
                continue

            low = text.lower()
            if not candidate_text_gate(path, low):
                continue

            roles = {}
            for role, spec in FINGERPRINTS.items():
                score, evidence = role_score(low, spec)
                if score > 0:
                    roles[role] = {
                        "score": int(score),
                        "evidence": evidence[:20],
                    }

            # Keep only meaningful candidates.
            if not roles:
                continue

            rows.append({
                "path": rel(path),
                "name": path.name,
                "size_bytes": int(path.stat().st_size),
                "sha256": sha256(path),
                "roles": roles,
                "metadata": extract_metadata(text),
            })

    return rows


def discover_checkpoints():
    rows = []
    for root in SEARCH_ROOTS:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or is_excluded(path):
                continue

            try:
                relative = path.relative_to(R)
                if relative.parts and relative.parts[0] == "output":
                    continue
            except ValueError:
                pass

            if not looks_like_checkpoint(path):
                continue

            size = int(path.stat().st_size)
            if size > MAX_CHECKPOINT_BYTES:
                rows.append({
                    "path": rel(path),
                    "name": path.name,
                    "size_bytes": size,
                    "sha256": None,
                    "status": "SKIPPED_TOO_LARGE",
                })
                continue

            rows.append({
                "path": rel(path),
                "name": path.name,
                "size_bytes": size,
                "sha256": sha256(path),
                "status": "HASHED_READ_ONLY",
            })
    return rows


def best_candidates(source_rows, role, minimum_score=3):
    eligible = []
    for row in source_rows:
        rec = row.get("roles", {}).get(role)
        if rec and rec["score"] >= minimum_score:
            eligible.append({
                "path": row["path"],
                "name": row["name"],
                "sha256": row["sha256"],
                "score": rec["score"],
                "evidence": rec["evidence"],
            })
    eligible.sort(key=lambda x: (-x["score"], x["path"]))
    return eligible


def write_csv(path: Path, source_rows):
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "path",
            "name",
            "size_bytes",
            "sha256",
            "role",
            "score",
            "evidence",
            "tensorflow",
            "lstm",
            "gru",
            "film",
            "fourier",
            "physics_loss",
            "godunov",
            "capillary",
            "compressible",
            "dykstra_parsons",
            "eight_layer",
            "tof",
            "pollock",
            "lorenz",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in source_rows:
            m = row["metadata"]
            for role, rec in row["roles"].items():
                writer.writerow({
                    "path": row["path"],
                    "name": row["name"],
                    "size_bytes": row["size_bytes"],
                    "sha256": row["sha256"],
                    "role": role,
                    "score": rec["score"],
                    "evidence": ";".join(rec["evidence"]),
                    "tensorflow": m["tensorflow_present"],
                    "lstm": m["lstm_present"],
                    "gru": m["gru_present"],
                    "film": m["film_present"],
                    "fourier": m["fourier_present"],
                    "physics_loss": m["physics_loss_present"],
                    "godunov": m["godunov_present"],
                    "capillary": m["capillary_present"],
                    "compressible": m["compressible_present"],
                    "dykstra_parsons": m["dykstra_parsons_present"],
                    "eight_layer": m["eight_layer_present"],
                    "tof": m["tof_present"],
                    "pollock": m["pollock_present"],
                    "lorenz": m["lorenz_present"],
                })


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-0A")
    print("Legacy BL / DP Model-Artifact Discovery + Provenance Inventory")
    print("=" * 78)

    print(
        "\nREAD-ONLY DISCOVERY — no TensorFlow import, no model/checkpoint load, "
        "no NPZ load, no OOD reopening, no training, no inference.\n"
    )

    if any(p.exists() for p in [INVENTORY, CANDIDATE_CSV, ROLE_REPORT, SUMMARY]):
        raise RuntimeError(
            "V16E-0A outputs already exist. Refusing to overwrite discovery record."
        )

    gates = {
        "E0_contract_SHA_valid": valid_sha256_literal(E0_CONTRACT_SHA),
        "E0_interface_SHA_valid": valid_sha256_literal(E0_INTERFACE_SHA),
        "E0_evidence_SHA_valid": valid_sha256_literal(E0_EVIDENCE_SHA),
        "E0_summary_SHA_valid": valid_sha256_literal(E0_SUMMARY_SHA),

        "E0_contract_SHA_exact": exact_sha(E0_CONTRACT, E0_CONTRACT_SHA),
        "E0_interface_SHA_exact": exact_sha(E0_INTERFACE, E0_INTERFACE_SHA),
        "E0_evidence_SHA_exact": exact_sha(E0_EVIDENCE, E0_EVIDENCE_SHA),
        "E0_summary_SHA_exact": exact_sha(E0_SUMMARY, E0_SUMMARY_SHA),
    }

    print("E0 AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-0A blocked: E0 authority mismatch.")

    e0 = read_json(E0_SUMMARY)
    gates.update({
        "E0_status_exact": e0.get("status") == EXPECTED_E0_STATUS,
        "E0_adapter_coding_not_authorized":
            e0.get("adapter_coding_authorized") is False,
        "E0_legacy_inventory_required":
            e0.get("legacy_model_inventory_required") is True,
    })

    source_rows = discover_sources()
    checkpoint_rows = discover_checkpoints()

    role_names = list(FINGERPRINTS)
    role_candidates = {
        role: best_candidates(source_rows, role)
        for role in role_names
    }

    # The round labels are intentionally unbound in discovery.
    explicit_bindings = {
        "BL_PI_RNN_ROUND_1": None,
        "BL_PI_RNN_ROUND_2": None,
        "BL_PI_RNN_ROUND_3": None,
        "HYBRID_DP_PI_RNN_OR_LAYER_RNN": None,
    }

    readiness = {
        "milestone": "V16E-0A",
        "policy":
            "Discovery only. Candidate rankings are fingerprints, not scientific role bindings.",
        "roles": {
            role: {
                "candidate_count": len(role_candidates[role]),
                "candidates": role_candidates[role][:20],
            }
            for role in role_names
        },
        "explicit_legacy_round_bindings": explicit_bindings,
        "checkpoint_candidates": checkpoint_rows,
        "binding_status": {
            "BL_Round_1_bound": False,
            "BL_Round_2_bound": False,
            "BL_Round_3_bound": False,
            "Hybrid_DP_learned_bound": False,
        },
        "next_requirement":
            "Review candidate inventory and bind exact legacy source/checkpoint identities "
            "without renaming ambiguous candidates.",
    }

    ROLE_REPORT.write_text(json.dumps(readiness, indent=2))

    inventory = {
        "milestone": "V16E-0A",
        "search_roots": [str(x) for x in SEARCH_ROOTS],
        "excluded_directories": sorted(EXCLUDED_DIR_NAMES),
        "source_candidate_count": len(source_rows),
        "checkpoint_candidate_count": len(checkpoint_rows),
        "source_candidates": source_rows,
        "checkpoint_candidates": checkpoint_rows,
        "role_readiness_path": str(ROLE_REPORT.relative_to(R)),
        "role_readiness_sha256": sha256(ROLE_REPORT),
        "execution": {
            "TensorFlow_import": False,
            "checkpoint_deserialization": False,
            "NPZ_load": False,
            "OOD_reopen": False,
            "model_inference": False,
            "training": False,
            "file_hashing_only": True,
        },
    }

    INVENTORY.write_text(json.dumps(inventory, indent=2))
    write_csv(CANDIDATE_CSV, source_rows)

    # Discovery is considered successful even if exact round bindings remain
    # unresolved. That is the scientifically correct outcome for an incomplete
    # local artifact set.
    gates.update({
        "inventory_written_nonempty":
            INVENTORY.exists() and INVENTORY.stat().st_size > 0,
        "candidate_CSV_written_nonempty":
            CANDIDATE_CSV.exists() and CANDIDATE_CSV.stat().st_size > 0,
        "role_report_written_nonempty":
            ROLE_REPORT.exists() and ROLE_REPORT.stat().st_size > 0,

        "no_TensorFlow_import_in_E0A": True,
        "no_checkpoint_deserialization_in_E0A": True,
        "no_NPZ_load_in_E0A": True,
        "no_OOD_reopen_in_E0A": True,
        "no_training_in_E0A": True,
        "no_inference_in_E0A": True,
        "no_ambiguous_round_binding_in_E0A": True,
        "adapter_coding_remains_unauthorized": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    # Readiness is descriptive, not a PASS/FAIL threshold.
    print("\nDISCOVERY COUNTS")
    print("  source candidates    :", len(source_rows))
    print("  checkpoint candidates:", len(checkpoint_rows))

    print("\nTOP ROLE CANDIDATES")
    for role in role_names:
        candidates = role_candidates[role]
        print(f"\n  {role}: {len(candidates)} candidate(s)")
        for c in candidates[:5]:
            print(
                "    score=%2d  %s  SHA=%s"
                % (c["score"], c["path"], c["sha256"][:16] + "...")
            )

    print("\nEXPLICIT LEGACY ROUND BINDINGS")
    print("  BL Round 1 : UNBOUND")
    print("  BL Round 2 : UNBOUND")
    print("  BL Round 3 : UNBOUND")
    print("  Hybrid DP  : UNBOUND")
    print("  Reason     : E0A never guesses from candidate fingerprints.")

    status = (
        "V16E_LEGACY_BL_DP_ARTIFACT_DISCOVERY_COMPLETE_"
        "EXACT_SHA_CANDIDATE_INVENTORY_FROZEN_"
        "AMBIGUOUS_LEGACY_ROUND_BINDINGS_REMAIN_UNBOUND_"
        "ADAPTER_CODING_NOT_AUTHORIZED"
        if ok
        else "V16E_E0A_LEGACY_DISCOVERY_BLOCKED"
    )

    summary = {
        "milestone": "V16E-0A",
        "status": status,

        "inventory_sha256": sha256(INVENTORY),
        "candidate_csv_sha256": sha256(CANDIDATE_CSV),
        "role_report_sha256": sha256(ROLE_REPORT),

        "source_candidate_count": len(source_rows),
        "checkpoint_candidate_count": len(checkpoint_rows),

        "explicit_round_bindings_complete": False,
        "adapter_coding_authorized": False,

        "next_milestone":
            "V16E-0B — Review E0A candidates and bind exact BL Round-1/2/3 + "
            "Hybrid DP learned source/checkpoint identities; if required artifacts "
            "are outside this project, import/copy those exact immutable files first.",

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print(
        "  V16E-0B — Review the candidate inventory and bind exact legacy "
        "BL Round-1/2/3 + Hybrid DP learned artifacts."
    )

    print("\nInventory SHA-256 :", sha256(INVENTORY))
    print("Candidates SHA-256:", sha256(CANDIDATE_CSV))
    print("Role report SHA-256:", sha256(ROLE_REPORT))
    print("Summary SHA-256   :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
