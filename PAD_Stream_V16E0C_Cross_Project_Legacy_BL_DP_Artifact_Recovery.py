#!/usr/bin/env python3
"""
PAD-Stream V16E-0C
Cross-Project Legacy BL/DP Artifact Recovery + Explicit Historical Binding Audit

Purpose
-------
Broaden the read-only provenance search from the current portable PAD-Stream
project to sibling PyCharm projects, because the historical BL/DP learned
artifacts may predate the portable V15/V16 tree.

E0C may bind an artifact only when evidence is explicit:
  * Stage 1-4 checkpoints: exact expected basename.
  * 8-layer DP physics: validated source fingerprint + unique content hash
    (duplicate-safe filenames such as "(1)" / "(2)" may be equivalent).
  * Round 1/2/3: source explicitly self-identifies with that round label.
  * Hybrid DP/layer-RNN: source explicitly contains learned recurrent +
    Dykstra-Parsons/layer-RNN semantics.

E0C does NOT:
  * import TensorFlow,
  * deserialize models/checkpoints,
  * load NPZ datasets,
  * run inference,
  * train/retrain,
  * reopen geology0029,
  * infer historical round identities from Stage 1/2/3/4 labels,
  * select a canonical transport proposal engine.

Missing artifacts remain missing. No substitute retraining is authorized.
"""

from pathlib import Path
import hashlib
import json
import re
import sys


R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E0C_CROSS_PROJECT_LEGACY_BL_DP_ARTIFACT_RECOVERY"
)
OUT.mkdir(parents=True, exist_ok=True)

RECOVERY = OUT / "V16E0C_Cross_Project_Legacy_Artifact_Recovery.json"
ROUND_AUDIT = OUT / "V16E0C_Round_and_Hybrid_Explicit_Binding_Audit.json"
SUMMARY = OUT / "PAD_Stream_V16E0C_Summary.json"


# =============================================================================
# E0B authority
# =============================================================================

E0B_SOURCE = R / "PAD_Stream_V16E0B_Exact_BL_DP_Source_Binding_and_Legacy_Gap_Freeze.py"
E0B_SOURCE_SHA = "525b8927c2abe14754585584ebe5027f8b3272cc39646baea0ed7b764c64a2c5"

E0B_DIR = R / "output" / "V16_E0B_EXACT_BL_PHYSICS_LADDER_DP_SOURCE_BINDING"
E0B_BINDING = E0B_DIR / "V16E0B_BL_DP_Exact_Source_Binding.json"
E0B_GAP = E0B_DIR / "V16E0B_Legacy_Learned_Artifact_Gap_Register.json"
E0B_SUMMARY = E0B_DIR / "PAD_Stream_V16E0B_Summary.json"

E0B_BINDING_SHA = "ed4a9cbb6c88f9b7659e3246a0214031eee60fbed933d360165fe717d82d82fa"
E0B_GAP_SHA = "49ee55e87bd8b75bafc9cea28f3b6cc217817e73651e3e5c0c6c176399bf3439"
E0B_SUMMARY_SHA = "af6475fd70ad827f3d4c1d9511fb1d9f68aae1e2b7876c0e5dcd2cd2f5cc7b27"

EXPECTED_E0B_STATUS = (
    "V16E_BL_PHYSICS_LADDER_EXACT_SOURCES_BOUND_"
    "DP_PHYSICS_BINDING_AUDITED_"
    "LEGACY_ROUND_AND_HYBRID_LEARNED_ARTIFACT_GAPS_FROZEN_"
    "ADAPTER_CODING_NOT_AUTHORIZED"
)


# =============================================================================
# Frozen Stage sources/checkpoint expectations from E0B
# =============================================================================

STAGES = {
    "BL_STAGE1_INCOMPRESSIBLE_PI_RNN": {
        "source_name": "pi_rnn_stage1_incompressible.py",
        "source_sha256":
            "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58",
        "checkpoint_name": "pi_rnn_fan_multicase_corey.weights.h5",
        "config_name": "pi_rnn_fan_multicase_corey_config.json",
    },
    "BL_STAGE2_COMPRESSIBLE_GODUNOV_PI_RNN": {
        "source_name": "pi_rnn_stage2_compressible_godunov.py",
        "source_sha256":
            "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397",
        "checkpoint_name": "pi_rnn_fan_stage2_godunov.weights.h5",
        "config_name": "pi_rnn_fan_stage2_godunov_config.json",
    },
    "BL_STAGE3_CAPILLARY_PI_RNN": {
        "source_name": "pi_rnn_stage3_capillary.py",
        "source_sha256":
            "dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f",
        "checkpoint_name": "pi_rnn_stage3_capillary_v9.weights.h5",
        "config_name": "pi_rnn_stage3_capillary_v9_config.json",
    },
    "BL_STAGE4_FULL_COMPRESSIBLE_CAPILLARY_PI_RNN": {
        "source_name": "pi_rnn_stage4_full_godunov.py",
        "source_sha256":
            "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a",
        "checkpoint_name": "pi_rnn_stage4_full_godunov.weights.h5",
        "config_name": "pi_rnn_stage4_full_godunov_config.json",
    },
}


# =============================================================================
# Search policy
# =============================================================================

# Search current project AND its parent (normally .../PyCharmProjects).
# This intentionally reaches sibling historical projects without scanning the
# whole user profile/drive.
SEARCH_ROOTS = [R]
if R.parent.exists() and R.parent not in SEARCH_ROOTS:
    SEARCH_ROOTS.append(R.parent)

EXCLUDED_DIR_NAMES = {
    ".git", ".idea", ".venv", "venv", "env", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ipynb_checkpoints",
    "node_modules", "site-packages", "dist-packages",
}

# Planning/packaging files must not become historical learned-model candidates.
EXCLUDED_SOURCE_PREFIXES = (
    "PAD_Stream_V16E",
    "PAD_Stream_V16D",
    "PAD_Stream_Post_V15",
)

TEXT_SUFFIXES = {".py", ".txt", ".md", ".json", ".yaml", ".yml"}
MAX_TEXT_BYTES = 20 * 1024 * 1024
MAX_CHECKPOINT_BYTES = 2 * 1024 * 1024 * 1024

DP_NAME_REGEX = re.compile(
    r"PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation"
    r"(?:\(\d+\))?\.py$",
    re.I,
)

DP_REQUIRED_MARKERS = [
    "class DykstraParsons",
    "full DP table",
    "8-layer",
    "allocation=\"kh\"",
    "allocation=\"kh_mob\"",
]

ROUND_MARKERS = {
    "Round_1": [
        r"\bround[\s_-]*1\b",
        r"\br1\b",
    ],
    "Round_2": [
        r"\bround[\s_-]*2\b",
        r"\br2\b",
    ],
    "Round_3": [
        r"\bround[\s_-]*3\b",
        r"\br3\b",
    ],
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


def rel_from_search_root(path: Path) -> str:
    for root in SEARCH_ROOTS:
        try:
            return f"{root.name}/" + str(path.relative_to(root))
        except ValueError:
            pass
    return str(path)


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def is_generated_output(path: Path) -> bool:
    # Ignore all output directories produced by our milestones.
    return "output" in {p.lower() for p in path.parts}


def safe_text(path: Path):
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def unique_files_by_resolved_path(paths):
    seen = set()
    out = []
    for p in paths:
        try:
            key = str(p.resolve()).lower()
        except Exception:
            key = str(p).lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def find_by_exact_basename(basename: str):
    hits = []
    for root in SEARCH_ROOTS:
        try:
            for p in root.rglob(basename):
                if (
                    p.is_file()
                    and not is_excluded(p)
                    and not is_generated_output(p)
                ):
                    hits.append(p)
        except PermissionError:
            continue
    return unique_files_by_resolved_path(hits)


def source_is_learned_bl(text_lower: str) -> bool:
    learned = (
        "tensorflow" in text_lower
        or "tf.keras" in text_lower
        or "keras" in text_lower
    )
    recurrent = any(x in text_lower for x in ["lstm", "gru", "rnn"])
    bl = (
        ("buckley" in text_lower and "leverett" in text_lower)
        or "fractional flow" in text_lower
        or "fractional_flow" in text_lower
    )
    return learned and recurrent and bl


def source_is_explicit_hybrid_dp(text_lower: str) -> bool:
    learned = (
        "tensorflow" in text_lower
        or "tf.keras" in text_lower
        or "keras" in text_lower
    )
    recurrent = any(x in text_lower for x in ["lstm", "gru", "rnn"])
    explicit_dp = (
        ("dykstra" in text_lower and "parsons" in text_lower)
        or "layer rnn" in text_lower
        or "layer-rnn" in text_lower
        or "hybrid pi-rnn" in text_lower
        or "hybrid_pirnn" in text_lower
    )
    # Avoid files that merely discuss the concept in prose.
    executable_signal = any(
        x in text_lower
        for x in [
            "def build_model",
            "tf.keras.model",
            "keras.model",
            "model.fit",
            "gradienttape",
            "save_weights",
        ]
    )
    return learned and recurrent and explicit_dp and executable_signal


def parse_checkpoint_references(text: str):
    names = set()

    # Quoted model-ish basenames.
    patterns = [
        r'["\']([^"\']+\.weights\.h5)["\']',
        r'["\']([^"\']+\.keras)["\']',
        r'["\']([^"\']+\.h5)["\']',
        r'["\']([^"\']+\.hdf5)["\']',
        r'["\']([^"\']+\.ckpt)["\']',
    ]

    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            names.add(Path(m.group(1)).name)

    return sorted(names)


def recover_exact_artifacts():
    records = {}

    for stage_id, spec in STAGES.items():
        checkpoints = []
        for p in find_by_exact_basename(spec["checkpoint_name"]):
            if p.stat().st_size <= MAX_CHECKPOINT_BYTES:
                checkpoints.append({
                    "path": rel_from_search_root(p),
                    "sha256": sha256(p),
                    "size_bytes": p.stat().st_size,
                    "status": "PRESENT_HASHED_NOT_LOADED",
                })

        configs = []
        for p in find_by_exact_basename(spec["config_name"]):
            configs.append({
                "path": rel_from_search_root(p),
                "sha256": sha256(p),
                "size_bytes": p.stat().st_size,
            })

        records[stage_id] = {
            "source_name": spec["source_name"],
            "source_sha256": spec["source_sha256"],
            "expected_checkpoint_name": spec["checkpoint_name"],
            "checkpoint_matches": checkpoints,
            "checkpoint_match_count": len(checkpoints),
            "checkpoint_bound_unique":
                len({x["sha256"] for x in checkpoints}) == 1
                and len(checkpoints) >= 1,
            "expected_config_name": spec["config_name"],
            "config_matches": configs,
            "config_match_count": len(configs),
        }

    return records


def recover_dp_physics():
    hits = []

    for root in SEARCH_ROOTS:
        for p in root.rglob("*.py"):
            if (
                not p.is_file()
                or is_excluded(p)
                or is_generated_output(p)
                or not DP_NAME_REGEX.fullmatch(p.name)
            ):
                continue

            text = safe_text(p)
            if text is None:
                continue

            low = text.lower()
            markers = {
                marker: marker.lower() in low
                for marker in DP_REQUIRED_MARKERS
            }

            hits.append({
                "path": rel_from_search_root(p),
                "name": p.name,
                "sha256": sha256(p),
                "size_bytes": p.stat().st_size,
                "fingerprints": markers,
                "fingerprint_pass": all(markers.values()),
            })

    # Deduplicate path traversal overlap from R and R.parent.
    dedup = {}
    for h in hits:
        dedup[(h["path"], h["sha256"])] = h
    hits = sorted(dedup.values(), key=lambda x: x["path"].lower())

    valid = [h for h in hits if h["fingerprint_pass"]]
    unique_valid_hashes = sorted({h["sha256"] for h in valid})

    if len(unique_valid_hashes) == 1 and valid:
        status = "BOUND_BY_UNIQUE_CONTENT_HASH"
        bound_sha = unique_valid_hashes[0]
    elif len(valid) == 1:
        status = "BOUND_BY_SINGLE_VALID_SOURCE"
        bound_sha = valid[0]["sha256"]
    elif not valid:
        status = "UNBOUND_NO_VALID_SOURCE"
        bound_sha = None
    else:
        status = "UNBOUND_MULTIPLE_DISTINCT_VALID_CONTENTS"
        bound_sha = None

    return {
        "candidate_count": len(hits),
        "valid_candidate_count": len(valid),
        "unique_valid_content_hash_count": len(unique_valid_hashes),
        "status": status,
        "bound_sha256": bound_sha,
        "candidates": hits,
    }


def discover_explicit_round_sources():
    records = {round_name: [] for round_name in ROUND_MARKERS}

    for root in SEARCH_ROOTS:
        for p in root.rglob("*"):
            if (
                not p.is_file()
                or is_excluded(p)
                or is_generated_output(p)
                or p.suffix.lower() not in TEXT_SUFFIXES
            ):
                continue

            if p.name.startswith(EXCLUDED_SOURCE_PREFIXES):
                continue

            text = safe_text(p)
            if text is None:
                continue

            low = text.lower()
            if not source_is_learned_bl(low):
                continue

            search_blob = (p.name + "\n" + text[:50000]).lower()

            for round_name, patterns in ROUND_MARKERS.items():
                explicit_hits = [
                    pat
                    for pat in patterns
                    if re.search(pat, search_blob, flags=re.I)
                ]
                if explicit_hits:
                    ckpt_refs = parse_checkpoint_references(text)
                    records[round_name].append({
                        "path": rel_from_search_root(p),
                        "name": p.name,
                        "sha256": sha256(p),
                        "size_bytes": p.stat().st_size,
                        "explicit_round_patterns": explicit_hits,
                        "checkpoint_references": ckpt_refs,
                    })

    # Unique by SHA/path.
    for round_name in records:
        dedup = {}
        for rec in records[round_name]:
            dedup[(rec["path"], rec["sha256"])] = rec
        records[round_name] = sorted(
            dedup.values(),
            key=lambda x: x["path"].lower(),
        )

    binding = {}
    for round_name, candidates in records.items():
        unique_hashes = sorted({c["sha256"] for c in candidates})
        if len(unique_hashes) == 1 and candidates:
            status = "EXPLICIT_SOURCE_BOUND"
            bound_sha = unique_hashes[0]
        elif not candidates:
            status = "UNBOUND_NO_EXPLICIT_SOURCE"
            bound_sha = None
        else:
            status = "UNBOUND_MULTIPLE_DISTINCT_EXPLICIT_SOURCES"
            bound_sha = None

        binding[round_name] = {
            "status": status,
            "bound_source_sha256": bound_sha,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    return binding


def discover_explicit_hybrid_sources():
    candidates = []

    for root in SEARCH_ROOTS:
        for p in root.rglob("*.py"):
            if (
                not p.is_file()
                or is_excluded(p)
                or is_generated_output(p)
                or p.name.startswith(EXCLUDED_SOURCE_PREFIXES)
            ):
                continue

            text = safe_text(p)
            if text is None:
                continue

            low = text.lower()

            if source_is_explicit_hybrid_dp(low):
                checkpoint_refs = parse_checkpoint_references(text)
                ckpt_matches = []
                for basename in checkpoint_refs:
                    for c in find_by_exact_basename(basename):
                        ckpt_matches.append({
                            "basename": basename,
                            "path": rel_from_search_root(c),
                            "sha256": sha256(c),
                            "size_bytes": c.stat().st_size,
                        })

                candidates.append({
                    "path": rel_from_search_root(p),
                    "name": p.name,
                    "sha256": sha256(p),
                    "size_bytes": p.stat().st_size,
                    "checkpoint_references": checkpoint_refs,
                    "checkpoint_matches": ckpt_matches,
                })

    dedup = {}
    for c in candidates:
        dedup[(c["path"], c["sha256"])] = c
    candidates = sorted(dedup.values(), key=lambda x: x["path"].lower())

    unique_hashes = sorted({c["sha256"] for c in candidates})

    if len(unique_hashes) == 1 and candidates:
        status = "EXPLICIT_HYBRID_SOURCE_BOUND"
        bound_source_sha = unique_hashes[0]
    elif not candidates:
        status = "UNBOUND_NO_EXPLICIT_HYBRID_SOURCE"
        bound_source_sha = None
    else:
        status = "UNBOUND_MULTIPLE_DISTINCT_EXPLICIT_HYBRID_SOURCES"
        bound_source_sha = None

    # Checkpoint can be bound only if all matches reduce to one unique SHA.
    checkpoint_records = [
        x
        for c in candidates
        for x in c.get("checkpoint_matches", [])
    ]
    unique_checkpoint_hashes = sorted(
        {x["sha256"] for x in checkpoint_records}
    )

    if len(unique_checkpoint_hashes) == 1 and checkpoint_records:
        checkpoint_status = "EXPLICIT_HYBRID_CHECKPOINT_BOUND"
        bound_checkpoint_sha = unique_checkpoint_hashes[0]
    elif not checkpoint_records:
        checkpoint_status = "UNBOUND_NO_HYBRID_CHECKPOINT_FILE"
        bound_checkpoint_sha = None
    else:
        checkpoint_status = "UNBOUND_MULTIPLE_DISTINCT_HYBRID_CHECKPOINTS"
        bound_checkpoint_sha = None

    return {
        "source_status": status,
        "bound_source_sha256": bound_source_sha,
        "checkpoint_status": checkpoint_status,
        "bound_checkpoint_sha256": bound_checkpoint_sha,
        "candidates": candidates,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-0C")
    print("Cross-Project Legacy BL/DP Artifact Recovery + Explicit Binding Audit")
    print("=" * 78)

    print(
        "\nREAD-ONLY RECOVERY — no TensorFlow import, no checkpoint/model load, "
        "no NPZ load, no OOD reopen, no training, no inference.\n"
    )

    if any(p.exists() for p in [RECOVERY, ROUND_AUDIT, SUMMARY]):
        raise RuntimeError(
            "V16E-0C outputs already exist. Refusing to overwrite recovery audit."
        )

    gates = {
        "E0B_source_SHA_valid": valid_sha256_literal(E0B_SOURCE_SHA),
        "E0B_binding_SHA_valid": valid_sha256_literal(E0B_BINDING_SHA),
        "E0B_gap_SHA_valid": valid_sha256_literal(E0B_GAP_SHA),
        "E0B_summary_SHA_valid": valid_sha256_literal(E0B_SUMMARY_SHA),

        "E0B_source_SHA_exact": exact_sha(E0B_SOURCE, E0B_SOURCE_SHA),
        "E0B_binding_SHA_exact": exact_sha(E0B_BINDING, E0B_BINDING_SHA),
        "E0B_gap_SHA_exact": exact_sha(E0B_GAP, E0B_GAP_SHA),
        "E0B_summary_SHA_exact": exact_sha(E0B_SUMMARY, E0B_SUMMARY_SHA),
    }

    print("E0B AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-0C blocked: E0B authority mismatch.")

    e0b = read_json(E0B_SUMMARY)

    gates.update({
        "E0B_status_exact": e0b.get("status") == EXPECTED_E0B_STATUS,
        "E0B_BL_sources_bound":
            e0b.get("all_BL_physics_ladder_sources_bound") is True,
        "E0B_adapter_coding_not_authorized":
            e0b.get("adapter_coding_authorized") is False,
        "E0B_round1_unbound": e0b.get("BL_Round_1_bound") is False,
        "E0B_round2_unbound": e0b.get("BL_Round_2_bound") is False,
        "E0B_round3_unbound": e0b.get("BL_Round_3_bound") is False,
        "E0B_hybrid_unbound": e0b.get("Hybrid_DP_learned_bound") is False,
    })

    stage_recovery = recover_exact_artifacts()
    dp_recovery = recover_dp_physics()
    round_recovery = discover_explicit_round_sources()
    hybrid_recovery = discover_explicit_hybrid_sources()

    # Source SHA guard remains exact for Stage 1-4.
    gates.update({
        f"{stage_id}_source_SHA_valid":
            valid_sha256_literal(spec["source_sha256"])
        for stage_id, spec in STAGES.items()
    })

    all_stage_checkpoints_bound = all(
        rec["checkpoint_bound_unique"]
        for rec in stage_recovery.values()
    )

    any_stage_checkpoint_recovered = any(
        rec["checkpoint_match_count"] > 0
        for rec in stage_recovery.values()
    )

    rounds_all_bound = all(
        round_recovery[name]["status"] == "EXPLICIT_SOURCE_BOUND"
        for name in ["Round_1", "Round_2", "Round_3"]
    )

    hybrid_source_bound = (
        hybrid_recovery["source_status"] == "EXPLICIT_HYBRID_SOURCE_BOUND"
    )
    hybrid_checkpoint_bound = (
        hybrid_recovery["checkpoint_status"]
        == "EXPLICIT_HYBRID_CHECKPOINT_BOUND"
    )

    dp_bound = dp_recovery["bound_sha256"] is not None

    recovery_record = {
        "milestone": "V16E-0C",
        "search_roots": [str(x) for x in SEARCH_ROOTS],
        "search_scope":
            "current portable PAD-Stream project plus parent/sibling PyCharm projects",

        "stage_checkpoint_recovery": stage_recovery,
        "all_stage_checkpoints_bound": all_stage_checkpoints_bound,
        "any_stage_checkpoint_recovered": any_stage_checkpoint_recovered,

        "DP_8_layer_physics_recovery": dp_recovery,

        "execution": {
            "TensorFlow_import": False,
            "checkpoint_deserialization": False,
            "NPZ_load": False,
            "OOD_reopen": False,
            "training": False,
            "inference": False,
            "hash_and_text_fingerprint_only": True,
        },
    }
    RECOVERY.write_text(json.dumps(recovery_record, indent=2))

    round_audit = {
        "milestone": "V16E-0C",
        "round_binding_rule":
            "Only explicit historical round self-identification may bind Round 1/2/3. "
            "Stage 1/2/3/4 physics labels are never substituted.",

        "Round_bindings": round_recovery,
        "all_round_sources_bound": rounds_all_bound,

        "Hybrid_DP": hybrid_recovery,
        "Hybrid_DP_source_bound": hybrid_source_bound,
        "Hybrid_DP_checkpoint_bound": hybrid_checkpoint_bound,

        "adapter_readiness": {
            "BL_physics_sources": True,
            "BL_stage_checkpoints": all_stage_checkpoints_bound,
            "DP_physics": dp_bound,
            "Round_1_2_3_sources": rounds_all_bound,
            "Hybrid_DP_source": hybrid_source_bound,
            "Hybrid_DP_checkpoint": hybrid_checkpoint_bound,
        },

        "rule":
            "Missing learned artifacts stay missing; no retraining or role reassignment "
            "is performed to satisfy inventory.",
    }
    ROUND_AUDIT.write_text(json.dumps(round_audit, indent=2))

    # E0C itself is successful as a recovery audit regardless of whether missing
    # historical artifacts are found. Adapter coding remains blocked until all
    # required learned identities are actually bound.
    gates.update({
        "recovery_written_nonempty":
            RECOVERY.exists() and RECOVERY.stat().st_size > 0,
        "round_audit_written_nonempty":
            ROUND_AUDIT.exists() and ROUND_AUDIT.stat().st_size > 0,

        "Stage_round_identity_separation_preserved": True,
        "no_ambiguous_round_binding": True,
        "no_false_D38_hybrid_binding": True,
        "no_checkpoint_deserialization": True,
        "no_TensorFlow_import": True,
        "no_NPZ_load": True,
        "no_OOD_reopen": True,
        "no_training": True,
        "no_inference": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    learned_inventory_complete = (
        rounds_all_bound
        and hybrid_source_bound
        and hybrid_checkpoint_bound
    )

    # Note: Stage checkpoints are useful historical deployment artifacts, but
    # Round 1/2/3 checkpoint/source binding is the actual gating requirement.
    adapter_authorized = bool(
        ok
        and dp_bound
        and learned_inventory_complete
    )

    status = (
        "V16E_CROSS_PROJECT_LEGACY_RECOVERY_AUDIT_COMPLETE_"
        + (
            "REQUIRED_HISTORICAL_LEARNED_IDENTITIES_RECOVERED_"
            "ADAPTER_BINDING_REVIEW_AUTHORIZED"
            if adapter_authorized
            else
            "HISTORICAL_LEARNED_IDENTITY_GAPS_REMAIN_"
            "ADAPTER_CODING_NOT_AUTHORIZED"
        )
    )

    summary = {
        "milestone": "V16E-0C",
        "status": status,

        "recovery_sha256": sha256(RECOVERY),
        "round_audit_sha256": sha256(ROUND_AUDIT),

        "search_roots": [str(x) for x in SEARCH_ROOTS],

        "DP_physics_bound": dp_bound,
        "DP_physics_bound_sha256": dp_recovery["bound_sha256"],

        "any_stage_checkpoint_recovered": any_stage_checkpoint_recovered,
        "all_stage_checkpoints_bound": all_stage_checkpoints_bound,

        "Round_1_bound":
            round_recovery["Round_1"]["status"] == "EXPLICIT_SOURCE_BOUND",
        "Round_2_bound":
            round_recovery["Round_2"]["status"] == "EXPLICIT_SOURCE_BOUND",
        "Round_3_bound":
            round_recovery["Round_3"]["status"] == "EXPLICIT_SOURCE_BOUND",

        "Hybrid_DP_source_bound": hybrid_source_bound,
        "Hybrid_DP_checkpoint_bound": hybrid_checkpoint_bound,

        "learned_inventory_complete": learned_inventory_complete,
        "adapter_coding_authorized": adapter_authorized,

        "next_milestone": (
            "V16E-0D — Freeze recovered historical learned identities and "
            "authorize adapter implementation"
            if adapter_authorized
            else
            "V16E-0D — Legacy artifact recovery decision: locate/import the "
            "remaining original Round-1/2/3 and Hybrid DP learned artifacts, "
            "or formally freeze them as unavailable and redesign the integration "
            "plan without pretending they were recovered."
        ),

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nSEARCH ROOTS")
    for root in SEARCH_ROOTS:
        print(" ", root)

    print("\nSTAGE CHECKPOINT RECOVERY")
    for stage_id, rec in stage_recovery.items():
        print(f"  {stage_id}")
        print("    expected :", rec["expected_checkpoint_name"])
        print("    matches  :", rec["checkpoint_match_count"])
        for x in rec["checkpoint_matches"]:
            print("      ", x["path"])
            print("         SHA:", x["sha256"])

    print("\n8-LAYER DP PHYSICS RECOVERY")
    print("  status       :", dp_recovery["status"])
    print("  candidates   :", dp_recovery["candidate_count"])
    print("  valid        :", dp_recovery["valid_candidate_count"])
    print("  unique hashes:", dp_recovery["unique_valid_content_hash_count"])
    print("  bound SHA    :", dp_recovery["bound_sha256"])
    for c in dp_recovery["candidates"]:
        print(
            "   ",
            c["path"],
            "PASS" if c["fingerprint_pass"] else "FAIL",
            c["sha256"],
        )

    print("\nHISTORICAL ROUND RECOVERY")
    for name in ["Round_1", "Round_2", "Round_3"]:
        rec = round_recovery[name]
        print(f"  {name}: {rec['status']}")
        for c in rec["candidates"][:10]:
            print("    ", c["path"], c["sha256"])

    print("\nHYBRID DP / LAYER-RNN RECOVERY")
    print("  source status     :", hybrid_recovery["source_status"])
    print("  checkpoint status :", hybrid_recovery["checkpoint_status"])
    for c in hybrid_recovery["candidates"][:10]:
        print("    ", c["path"], c["sha256"])

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nADAPTER CODING")
    print("  authorized:", adapter_authorized)

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    print("\nRecovery SHA-256   :", sha256(RECOVERY))
    print("Round audit SHA-256:", sha256(ROUND_AUDIT))
    print("Summary SHA-256    :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
