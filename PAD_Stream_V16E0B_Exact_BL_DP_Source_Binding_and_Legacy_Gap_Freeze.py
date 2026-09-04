#!/usr/bin/env python3
"""
PAD-Stream V16E-0B
Exact BL Physics-Ladder + 8-Layer DP Source Binding
and Legacy Learned-Artifact Gap Freeze

Purpose
-------
Bind exact local executable source identities that are now unambiguous after
V16E-0A discovery, while preserving unresolved historical maturity labels.

This milestone binds:
  * Stage 1 incompressible BL PI-RNN source,
  * Stage 2 conservative compressible Godunov BL PI-RNN source,
  * Stage 3 capillary BL PI-RNN source,
  * Stage 4 full compressible-capillary Godunov BL PI-RNN source,
  * canonical 8-layer Dykstra-Parsons physics benchmark if the exact
    v14 Complete Validation source is present.

It DOES NOT equate Stage 1/2/3/4 with roadmap Round 1/2/3.
It DOES NOT invent a Hybrid DP learned artifact.
It DOES NOT load TensorFlow, checkpoints, NPZs, or OOD arrays.
It DOES NOT authorize adapter coding unless all legacy learned identities
required by V16E-0 are recovered in a later milestone.
"""

from pathlib import Path
import hashlib
import json
import re
import sys


R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E0B_EXACT_BL_PHYSICS_LADDER_DP_SOURCE_BINDING"
)
OUT.mkdir(parents=True, exist_ok=True)

BINDING = OUT / "V16E0B_BL_DP_Exact_Source_Binding.json"
GAP = OUT / "V16E0B_Legacy_Learned_Artifact_Gap_Register.json"
SUMMARY = OUT / "PAD_Stream_V16E0B_Summary.json"


# =============================================================================
# V16E-0A authority
# =============================================================================

E0A_SOURCE = R / "PAD_Stream_V16E0A_Legacy_BL_DP_Artifact_Discovery_Inventory.py"
E0A_SOURCE_SHA = "846cf8c278d9140e38ec11703e97ddd258d98465a7a66039a9b4838b3c74354e"

E0A_DIR = R / "output" / "V16_E0A_LEGACY_BL_DP_MODEL_ARTIFACT_DISCOVERY_INVENTORY"
E0A_INVENTORY = E0A_DIR / "V16E0A_Legacy_BL_DP_Artifact_Inventory.json"
E0A_CANDIDATES = E0A_DIR / "V16E0A_Legacy_BL_DP_Candidates.csv"
E0A_ROLE_REPORT = E0A_DIR / "V16E0A_Legacy_Role_Binding_Readiness.json"
E0A_SUMMARY = E0A_DIR / "PAD_Stream_V16E0A_Summary.json"

E0A_INVENTORY_SHA = "c82aa3f5cb87cfd2df5b71cdecae104f0a452394a9067a3ca3671e4db04d36b6"
E0A_CANDIDATES_SHA = "6b44904270f8e8f8a81b0f6e317e5628d06a8026e59ef219237440551e641a76"
E0A_ROLE_REPORT_SHA = "c04de232461fd7fa12cca8411bc8d334203c1842e3040f6cefe1abbeb26edc1b"
E0A_SUMMARY_SHA = "02fad1b3c3be2fba02fecff150ce5df1260d081ea2ed066f415763a4b6f22b0e"

EXPECTED_E0A_STATUS = (
    "V16E_LEGACY_BL_DP_ARTIFACT_DISCOVERY_COMPLETE_"
    "EXACT_SHA_CANDIDATE_INVENTORY_FROZEN_"
    "AMBIGUOUS_LEGACY_ROUND_BINDINGS_REMAIN_UNBOUND_"
    "ADAPTER_CODING_NOT_AUTHORIZED"
)


# =============================================================================
# Exact local source names now identified
# =============================================================================

BL_STAGE_SPECS = {
    "BL_STAGE1_INCOMPRESSIBLE_PI_RNN": {
        "filename": "pi_rnn_stage1_incompressible.py",
        "role":
            "Incompressible/multi-case Buckley-Leverett PI-RNN physics-ladder source",
        "must_contain": [
            "Physics-Informed Recurrent Neural Network for Buckley-Leverett Displacement",
            "tensorflow",
            "lambda_phys",
            "fractional",
        ],
        "expected_weight_basename": "pi_rnn_fan_multicase_corey.weights.h5",
        "expected_config_basename": "pi_rnn_fan_multicase_corey_config.json",
    },

    "BL_STAGE2_COMPRESSIBLE_GODUNOV_PI_RNN": {
        "filename": "pi_rnn_stage2_compressible_godunov.py",
        "role":
            "Conservative-form compressible Godunov Buckley-Leverett PI-RNN",
        "must_contain": [
            "STAGE 2 GODUNOV VARIANT",
            "CONSERVATIVE form",
            "CompressibleBLSolver",
            "tensorflow",
        ],
        "expected_weight_basename": "pi_rnn_fan_stage2_godunov.weights.h5",
        "expected_config_basename": "pi_rnn_fan_stage2_godunov_config.json",
    },

    "BL_STAGE3_CAPILLARY_PI_RNN": {
        "filename": "pi_rnn_stage3_capillary.py",
        "role":
            "Capillary Buckley-Leverett PI-RNN with advection-diffusion PDE residual",
        "must_contain": [
            "STAGE 3: CAPILLARY PRESSURE ONLY",
            "pde_residual_loss",
            "implicit",
            "tensorflow",
        ],
        "expected_weight_basename": "pi_rnn_stage3_capillary_v9.weights.h5",
        "expected_config_basename": "pi_rnn_stage3_capillary_v9_config.json",
    },

    "BL_STAGE4_FULL_COMPRESSIBLE_CAPILLARY_PI_RNN": {
        "filename": "pi_rnn_stage4_full_godunov.py",
        "role":
            "Full compressible-capillary Godunov Buckley-Leverett PI-RNN source",
        "must_contain": [
            "pi_rnn_stage4_full_godunov.weights.h5",
            "Pe_c",
            "Nc",
            "tensorflow",
        ],
        "expected_weight_basename": "pi_rnn_stage4_full_godunov.weights.h5",
        "expected_config_basename": "pi_rnn_stage4_full_godunov_config.json",
    },
}

DP_CANONICAL_FILENAME = "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"

DP_REQUIRED_MARKERS = [
    "class DykstraParsons",
    "allocation=\"kh\"",
    "allocation=\"kh_mob\"",
    "full DP table",
    "8-layer",
]


EXCLUDED_DIRS = {
    ".git", ".idea", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ipynb_checkpoints", "node_modules",
}


# =============================================================================
# Helpers
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


def excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def find_exact_basename(basename: str):
    matches = []
    for p in R.rglob(basename):
        if p.is_file() and not excluded(p):
            # Do not treat generated output copies as legacy source authority.
            try:
                rp = p.relative_to(R)
                if rp.parts and rp.parts[0] == "output":
                    continue
            except ValueError:
                pass
            matches.append(p)
    return sorted(matches)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def source_binding(spec_id: str, spec: dict):
    matches = find_exact_basename(spec["filename"])

    record = {
        "binding_id": spec_id,
        "role": spec["role"],
        "expected_filename": spec["filename"],
        "source_match_count": len(matches),
        "source_bound": False,
        "source": None,
        "fingerprint_gates": {},
        "expected_weight_basename": spec["expected_weight_basename"],
        "expected_config_basename": spec["expected_config_basename"],
        "weight_artifacts": [],
        "config_artifacts": [],
    }

    # Exact role binding requires exactly one executable source by basename.
    if len(matches) == 1:
        src = matches[0]
        txt = read_text(src)

        fingerprints = {
            marker: (marker.lower() in txt.lower())
            for marker in spec["must_contain"]
        }

        save_weight_reference = (
            spec["expected_weight_basename"].lower() in txt.lower()
        )
        config_reference = (
            spec["expected_config_basename"].lower() in txt.lower()
        )

        fingerprints[
            "source_references_expected_weight_basename"
        ] = save_weight_reference
        fingerprints[
            "source_references_expected_config_basename"
        ] = config_reference

        record["fingerprint_gates"] = fingerprints

        if all(fingerprints.values()):
            record["source_bound"] = True
            record["source"] = {
                "path": rel(src),
                "sha256": sha256(src),
                "size_bytes": src.stat().st_size,
            }

    # Checkpoint/config discovery is exact-basename only; no deserialization.
    weight_matches = find_exact_basename(spec["expected_weight_basename"])
    for p in weight_matches:
        record["weight_artifacts"].append({
            "path": rel(p),
            "sha256": sha256(p),
            "size_bytes": p.stat().st_size,
            "status": "PRESENT_HASHED_NOT_LOADED",
        })

    config_matches = find_exact_basename(spec["expected_config_basename"])
    for p in config_matches:
        record["config_artifacts"].append({
            "path": rel(p),
            "sha256": sha256(p),
            "size_bytes": p.stat().st_size,
            "status": "PRESENT_HASHED_NOT_EXECUTED",
        })

    record["checkpoint_present"] = len(record["weight_artifacts"]) > 0
    record["config_present"] = len(record["config_artifacts"]) > 0

    if not record["checkpoint_present"]:
        record["checkpoint_status"] = "EXPECTED_BY_SOURCE_BUT_NOT_PRESENT_LOCALLY"
    else:
        record["checkpoint_status"] = "PRESENT_HASHED_NOT_LOADED"

    return record


def bind_dp_physics():
    matches = find_exact_basename(DP_CANONICAL_FILENAME)

    record = {
        "binding_id": "DP_8_LAYER_CANONICAL_PHYSICS_BENCHMARK",
        "expected_filename": DP_CANONICAL_FILENAME,
        "source_match_count": len(matches),
        "source_bound": False,
        "source": None,
        "fingerprint_gates": {},
        "scientific_role": (
            "Controlled 8-layer no-crossflow Dykstra-Parsons physics benchmark "
            "for rate allocation, local PVI, breakthrough ordering, and "
            "flux-weighted aggregation."
        ),
    }

    if len(matches) == 1:
        src = matches[0]
        txt = read_text(src)
        gates = {
            marker: marker.lower() in txt.lower()
            for marker in DP_REQUIRED_MARKERS
        }
        record["fingerprint_gates"] = gates

        if all(gates.values()):
            record["source_bound"] = True
            record["source"] = {
                "path": rel(src),
                "sha256": sha256(src),
                "size_bytes": src.stat().st_size,
            }

    return record


def search_learned_hybrid_candidates():
    """
    Conservative local search for actual learned DP/Hybrid sources.
    Excludes V16E planning/contract files and PAD-Stream physics-only files
    unless they explicitly import TensorFlow/Keras.
    """
    candidates = []

    for p in R.rglob("*.py"):
        if not p.is_file() or excluded(p):
            continue

        try:
            rp = p.relative_to(R)
            if rp.parts and rp.parts[0] == "output":
                continue
        except ValueError:
            pass

        name_low = p.name.lower()
        if name_low.startswith("pad_stream_v16e"):
            continue

        txt = read_text(p)
        low = txt.lower()

        learned = ("tensorflow" in low or "tf.keras" in low or "keras" in low)
        recurrent = any(x in low for x in ["lstm", "gru", "rnn"])
        dp = (
            ("dykstra" in low and "parsons" in low)
            or (
                "layer" in low
                and "rate fraction" in low
                and "pore volume" in low
                and "heterogeneity" in low
            )
        )

        if learned and recurrent and dp:
            candidates.append({
                "path": rel(p),
                "sha256": sha256(p),
                "size_bytes": p.stat().st_size,
                "tensorflow_or_keras": True,
                "recurrent": True,
                "DP_or_layer_heterogeneity": True,
            })

    return candidates


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-0B")
    print("Exact BL Physics-Ladder + 8-Layer DP Source Binding")
    print("=" * 78)

    print(
        "\nREAD-ONLY BINDING — no TensorFlow import, no checkpoint/model load, "
        "no NPZ load, no OOD reopen, no training, no inference.\n"
    )

    if any(p.exists() for p in [BINDING, GAP, SUMMARY]):
        raise RuntimeError(
            "V16E-0B outputs already exist. Refusing to overwrite frozen binding."
        )

    gates = {
        "E0A_source_SHA_valid": valid_sha256_literal(E0A_SOURCE_SHA),
        "E0A_inventory_SHA_valid": valid_sha256_literal(E0A_INVENTORY_SHA),
        "E0A_candidates_SHA_valid": valid_sha256_literal(E0A_CANDIDATES_SHA),
        "E0A_role_report_SHA_valid": valid_sha256_literal(E0A_ROLE_REPORT_SHA),
        "E0A_summary_SHA_valid": valid_sha256_literal(E0A_SUMMARY_SHA),

        "E0A_source_SHA_exact": exact_sha(E0A_SOURCE, E0A_SOURCE_SHA),
        "E0A_inventory_SHA_exact": exact_sha(E0A_INVENTORY, E0A_INVENTORY_SHA),
        "E0A_candidates_SHA_exact": exact_sha(E0A_CANDIDATES, E0A_CANDIDATES_SHA),
        "E0A_role_report_SHA_exact": exact_sha(E0A_ROLE_REPORT, E0A_ROLE_REPORT_SHA),
        "E0A_summary_SHA_exact": exact_sha(E0A_SUMMARY, E0A_SUMMARY_SHA),
    }

    print("E0A AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-0B blocked: E0A authority mismatch.")

    e0a_summary = read_json(E0A_SUMMARY)
    gates.update({
        "E0A_status_exact":
            e0a_summary.get("status") == EXPECTED_E0A_STATUS,
        "E0A_explicit_round_bindings_incomplete":
            e0a_summary.get("explicit_round_bindings_complete") is False,
        "E0A_adapter_coding_not_authorized":
            e0a_summary.get("adapter_coding_authorized") is False,
        "E0A_checkpoint_count_zero":
            int(e0a_summary.get("checkpoint_candidate_count", -1)) == 0,
    })

    stage_bindings = {
        key: source_binding(key, spec)
        for key, spec in BL_STAGE_SPECS.items()
    }

    dp_binding = bind_dp_physics()
    hybrid_candidates = search_learned_hybrid_candidates()

    all_stage_sources_bound = all(
        rec["source_bound"] for rec in stage_bindings.values()
    )

    gates.update({
        "BL_stage1_source_bound":
            stage_bindings["BL_STAGE1_INCOMPRESSIBLE_PI_RNN"]["source_bound"],
        "BL_stage2_source_bound":
            stage_bindings["BL_STAGE2_COMPRESSIBLE_GODUNOV_PI_RNN"]["source_bound"],
        "BL_stage3_source_bound":
            stage_bindings["BL_STAGE3_CAPILLARY_PI_RNN"]["source_bound"],
        "BL_stage4_source_bound":
            stage_bindings[
                "BL_STAGE4_FULL_COMPRESSIBLE_CAPILLARY_PI_RNN"
            ]["source_bound"],
        "all_BL_physics_ladder_sources_bound":
            all_stage_sources_bound,

        # A canonical DP source can remain unresolved without invalidating the
        # BL source freeze; but if present, it must pass fingerprints.
        "DP_binding_valid_if_present":
            (
                dp_binding["source_match_count"] == 0
                or dp_binding["source_bound"]
            ),

        "roadmap_Round1_not_equated_to_Stage1": True,
        "roadmap_Round2_not_equated_to_Stage2": True,
        "roadmap_Round3_not_equated_to_Stage3_or_Stage4": True,

        "no_checkpoint_deserialization": True,
        "no_TensorFlow_import": True,
        "no_NPZ_load": True,
        "no_OOD_reopen": True,
        "no_training": True,
        "no_inference": True,
    })

    binding_record = {
        "milestone": "V16E-0B",
        "binding_role":
            "Exact source binding for BL physics ladder and canonical DP "
            "physics benchmark; learned historical maturity labels remain separate.",

        "upstream_E0A": {
            "source_sha256": E0A_SOURCE_SHA,
            "inventory_sha256": E0A_INVENTORY_SHA,
            "candidates_sha256": E0A_CANDIDATES_SHA,
            "role_report_sha256": E0A_ROLE_REPORT_SHA,
            "summary_sha256": E0A_SUMMARY_SHA,
        },

        "BL_physics_ladder": stage_bindings,

        "DP_8_layer_physics": dp_binding,

        "legacy_round_policy": {
            "Round_1": {
                "definition": "Earliest validated PI-RNN",
                "source_binding": None,
                "checkpoint_binding": None,
            },
            "Round_2": {
                "definition": "Expanded/conditioned PI-RNN",
                "source_binding": None,
                "checkpoint_binding": None,
            },
            "Round_3": {
                "definition": "Most complete BL PI-RNN",
                "source_binding": None,
                "checkpoint_binding": None,
            },
            "rule":
                "Physics Stage 1/2/3/4 labels are not substituted for Round "
                "1/2/3 maturity labels without direct historical evidence.",
        },

        "learned_hybrid_DP_candidates": hybrid_candidates,

        "checkpoint_policy": {
            "E0A_checkpoint_candidates": 0,
            "stage_expected_weight_files": {
                key: rec["expected_weight_basename"]
                for key, rec in stage_bindings.items()
            },
            "rule":
                "Expected checkpoint names extracted from source are not treated "
                "as trained checkpoint identities unless the actual file exists "
                "and is SHA-bound.",
        },

        "adapter_coding_authorized": False,
    }

    BINDING.write_text(json.dumps(binding_record, indent=2))

    missing_stage_checkpoints = [
        {
            "binding_id": key,
            "expected_weight_basename": rec["expected_weight_basename"],
        }
        for key, rec in stage_bindings.items()
        if not rec["checkpoint_present"]
    ]

    gap_record = {
        "milestone": "V16E-0B",
        "unresolved_required_legacy_artifacts": {
            "BL_Round_1_source_checkpoint": "UNBOUND",
            "BL_Round_2_source_checkpoint": "UNBOUND",
            "BL_Round_3_source_checkpoint": "UNBOUND",
            "Hybrid_DP_PI_RNN_or_layer_RNN_source_checkpoint":
                (
                    "CANDIDATES_FOUND_NEED_REVIEW"
                    if hybrid_candidates
                    else "NOT_FOUND_IN_LOCAL_PROJECT"
                ),
        },

        "BL_physics_ladder_checkpoint_gaps":
            missing_stage_checkpoints,

        "DP_physics_binding_status":
            (
                "BOUND"
                if dp_binding["source_bound"]
                else "CANONICAL_SOURCE_NOT_UNIQUELY_BOUND"
            ),

        "why_adapter_coding_remains_blocked":
            [
                "Roadmap Round 1/2/3 learned identities remain unbound.",
                "No actual BL physics-ladder checkpoint files were discovered by E0A.",
                "Hybrid DP learned source/checkpoint is not yet frozen.",
                "Canonical learned transport selector remains intentionally deferred.",
            ],

        "recovery_rule":
            "Recover/import the exact immutable legacy learned source/checkpoint "
            "artifacts; do not retrain substitutes merely to satisfy inventory.",
    }

    GAP.write_text(json.dumps(gap_record, indent=2))

    gates.update({
        "binding_written_nonempty":
            BINDING.exists() and BINDING.stat().st_size > 0,
        "gap_register_written_nonempty":
            GAP.exists() and GAP.stat().st_size > 0,
        "legacy_rounds_remain_unbound": True,
        "Hybrid_DP_binding_not_invented": True,
        "expected_checkpoint_names_not_treated_as_actual_checkpoints": True,
        "adapter_coding_remains_unauthorized": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    status = (
        "V16E_BL_PHYSICS_LADDER_EXACT_SOURCES_BOUND_"
        "DP_PHYSICS_BINDING_AUDITED_"
        "LEGACY_ROUND_AND_HYBRID_LEARNED_ARTIFACT_GAPS_FROZEN_"
        "ADAPTER_CODING_NOT_AUTHORIZED"
        if ok
        else "V16E_E0B_SOURCE_BINDING_BLOCKED"
    )

    summary = {
        "milestone": "V16E-0B",
        "status": status,

        "binding_sha256": sha256(BINDING),
        "gap_register_sha256": sha256(GAP),

        "all_BL_physics_ladder_sources_bound": all_stage_sources_bound,
        "DP_physics_source_bound": dp_binding["source_bound"],
        "Hybrid_DP_candidate_count": len(hybrid_candidates),

        "BL_Round_1_bound": False,
        "BL_Round_2_bound": False,
        "BL_Round_3_bound": False,
        "Hybrid_DP_learned_bound": False,

        "adapter_coding_authorized": False,

        "next_milestone":
            "V16E-0C — Recover and bind exact historical BL Round-1/2/3 "
            "and Hybrid DP learned source/checkpoint identities; preserve "
            "missing artifacts as missing rather than retraining replacements.",

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nEXACT BL PHYSICS-LADDER SOURCE BINDINGS")
    for key, rec in stage_bindings.items():
        print(f"\n  {key}")
        print("    source bound :", rec["source_bound"])
        if rec["source"]:
            print("    path         :", rec["source"]["path"])
            print("    SHA-256      :", rec["source"]["sha256"])
        print("    checkpoint   :", rec["checkpoint_status"])
        print("    expected     :", rec["expected_weight_basename"])

    print("\n8-LAYER DP PHYSICS")
    print("  source bound :", dp_binding["source_bound"])
    if dp_binding["source"]:
        print("  path         :", dp_binding["source"]["path"])
        print("  SHA-256      :", dp_binding["source"]["sha256"])

    print("\nLEARNED HYBRID DP")
    print("  local learned candidate count:", len(hybrid_candidates))
    for c in hybrid_candidates[:10]:
        print("   ", c["path"], c["sha256"][:16] + "...")

    print("\nROADMAP MATURITY ROUNDS")
    print("  Round 1 : UNBOUND — earliest validated PI-RNN")
    print("  Round 2 : UNBOUND — expanded/conditioned PI-RNN")
    print("  Round 3 : UNBOUND — most complete BL PI-RNN")
    print("  Stage labels are NOT substituted for round labels.")

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print(
        "  V16E-0C — Recover exact legacy Round-1/2/3 and Hybrid DP "
        "learned source/checkpoint identities."
    )

    print("\nBinding SHA-256     :", sha256(BINDING))
    print("Gap register SHA-256:", sha256(GAP))
    print("Summary SHA-256     :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
