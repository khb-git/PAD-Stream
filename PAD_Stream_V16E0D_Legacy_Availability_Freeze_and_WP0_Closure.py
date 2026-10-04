#!/usr/bin/env python3
"""
PAD-Stream V16E-0D
Legacy Artifact Availability Freeze + WP0 Closure + Prospective Reproduction Handoff

Purpose
-------
Close the architecture-reconciliation / provenance-recovery phase (V16E-0)
without inventing missing historical learned artifacts.

Frozen conclusions
------------------
1. Exact BL Stage 1-4 source code is recovered and SHA-bound.
2. Canonical 8-layer Dykstra-Parsons physics source is recovered from the
   project/library archive and must be present locally with its exact SHA.
3. Original historical BL Round 1/2/3 learned source/checkpoint identities
   remain unavailable after local, sibling-project, and library recovery.
4. Original Hybrid DP PI-RNN / layer-RNN learned source/checkpoint identities
   remain unavailable.
5. New V16E reproductions MAY be created from the recovered exact sources,
   but they must receive new experiment identities and may never be relabeled
   as the missing historical checkpoints.

This milestone:
  * imports no TensorFlow,
  * loads no checkpoint/model,
  * loads no NPZ,
  * reopens no OOD arrays,
  * performs no training or inference,
  * does not modify EXP-CS1.

It closes WP0 and authorizes a NEW prospective reproduction/integration branch.
"""

from pathlib import Path
import hashlib
import json
import sys

R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E0D_LEGACY_AVAILABILITY_FREEZE_AND_WP0_CLOSURE"
)
OUT.mkdir(parents=True, exist_ok=True)

FREEZE = OUT / "V16E0D_Legacy_Artifact_Availability_Freeze.json"
HANDOFF = OUT / "V16E0D_Prospective_Reproduction_Integration_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E0D_Summary.json"


# =============================================================================
# V16E-0C authority
# =============================================================================

E0C_SOURCE = R / "PAD_Stream_V16E0C_Cross_Project_Legacy_BL_DP_Artifact_Recovery.py"
E0C_SOURCE_SHA = "e3e192e62d1d7549a2b2d30c44f1d4e6e1f476ee4bd2675f3bc1deb640952289"

E0C_DIR = R / "output" / "V16_E0C_CROSS_PROJECT_LEGACY_BL_DP_ARTIFACT_RECOVERY"
E0C_RECOVERY = E0C_DIR / "V16E0C_Cross_Project_Legacy_Artifact_Recovery.json"
E0C_ROUND_AUDIT = E0C_DIR / "V16E0C_Round_and_Hybrid_Explicit_Binding_Audit.json"
E0C_SUMMARY = E0C_DIR / "PAD_Stream_V16E0C_Summary.json"

E0C_RECOVERY_SHA = "56ec9e5562f6dc3ebfa99c6f9790d0409b608621c74531c966c850d986fcd747"
E0C_ROUND_AUDIT_SHA = "f05b40ba77f99c3acbef0625faa7df3dce69341b27c7fad9d1635a6c33c56a84"
E0C_SUMMARY_SHA = "f665e3daab260d0d33effafd2ba25aa1e2df94bccfe108a10a9ae0d98cd8c9b5"

EXPECTED_E0C_STATUS = (
    "V16E_CROSS_PROJECT_LEGACY_RECOVERY_AUDIT_COMPLETE_"
    "HISTORICAL_LEARNED_IDENTITY_GAPS_REMAIN_"
    "ADAPTER_CODING_NOT_AUTHORIZED"
)


# =============================================================================
# Recovered exact BL source authorities
# =============================================================================

BL_SOURCES = {
    "Stage1_incompressible": {
        "path": R / "pi_rnn_stage1_incompressible.py",
        "sha256": "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58",
    },
    "Stage2_compressible_godunov": {
        "path": R / "pi_rnn_stage2_compressible_godunov.py",
        "sha256": "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397",
    },
    "Stage3_capillary": {
        "path": R / "pi_rnn_stage3_capillary.py",
        "sha256": "dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f",
    },
    "Stage4_full_compressible_capillary": {
        "path": R / "pi_rnn_stage4_full_godunov.py",
        "sha256": "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a",
    },
}


# =============================================================================
# Recovered 8-layer DP source authority
# =============================================================================

DP_SOURCE = R / "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"
DP_SOURCE_SHA = "45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6"

DP_MARKERS = [
    "class DykstraParsons",
    'allocation="kh"',
    'allocation="kh_mob"',
    "full DP table",
    "8-layer",
]


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


def main():
    print("=" * 78)
    print("PAD-Stream V16E-0D")
    print("Legacy Artifact Availability Freeze + WP0 Closure")
    print("=" * 78)

    print(
        "\nARCHIVAL / HANDOFF ONLY — no TensorFlow, no model/checkpoint load, "
        "no NPZ, no OOD reopening, no training, no inference.\n"
    )

    if any(p.exists() for p in [FREEZE, HANDOFF, SUMMARY]):
        raise RuntimeError(
            "V16E-0D outputs already exist. Refusing to overwrite frozen closure."
        )

    gates = {
        "E0C_source_SHA_valid": valid_sha256_literal(E0C_SOURCE_SHA),
        "E0C_recovery_SHA_valid": valid_sha256_literal(E0C_RECOVERY_SHA),
        "E0C_round_audit_SHA_valid": valid_sha256_literal(E0C_ROUND_AUDIT_SHA),
        "E0C_summary_SHA_valid": valid_sha256_literal(E0C_SUMMARY_SHA),

        "E0C_source_SHA_exact": exact_sha(E0C_SOURCE, E0C_SOURCE_SHA),
        "E0C_recovery_SHA_exact": exact_sha(E0C_RECOVERY, E0C_RECOVERY_SHA),
        "E0C_round_audit_SHA_exact": exact_sha(E0C_ROUND_AUDIT, E0C_ROUND_AUDIT_SHA),
        "E0C_summary_SHA_exact": exact_sha(E0C_SUMMARY, E0C_SUMMARY_SHA),
    }

    print("E0C AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("V16E-0D blocked: E0C authority mismatch.")

    e0c = read_json(E0C_SUMMARY)

    gates.update({
        "E0C_status_exact":
            e0c.get("status") == EXPECTED_E0C_STATUS,
        "E0C_Round1_unbound":
            e0c.get("Round_1_bound") is False,
        "E0C_Round2_unbound":
            e0c.get("Round_2_bound") is False,
        "E0C_Round3_unbound":
            e0c.get("Round_3_bound") is False,
        "E0C_Hybrid_source_unbound":
            e0c.get("Hybrid_DP_source_bound") is False,
        "E0C_Hybrid_checkpoint_unbound":
            e0c.get("Hybrid_DP_checkpoint_bound") is False,
        "E0C_adapter_not_authorized":
            e0c.get("adapter_coding_authorized") is False,
    })

    # -------------------------------------------------------------------------
    # Re-bind exact BL source authorities.
    # -------------------------------------------------------------------------

    for name, rec in BL_SOURCES.items():
        gates[f"{name}_SHA_literal_valid"] = valid_sha256_literal(rec["sha256"])
        gates[f"{name}_source_SHA_exact"] = exact_sha(rec["path"], rec["sha256"])

    # -------------------------------------------------------------------------
    # Bind recovered DP physics source.
    # -------------------------------------------------------------------------

    gates["DP_source_SHA_literal_valid"] = valid_sha256_literal(DP_SOURCE_SHA)
    gates["DP_source_SHA_exact"] = exact_sha(DP_SOURCE, DP_SOURCE_SHA)

    if DP_SOURCE.exists():
        dp_text = DP_SOURCE.read_text(encoding="utf-8", errors="replace").lower()
    else:
        dp_text = ""

    for marker in DP_MARKERS:
        gates[f"DP_marker_{marker}"] = marker.lower() in dp_text

    if not all(gates.values()):
        print("\nRECOVERY BINDING GATES")
        for k, v in gates.items():
            print("[PASS]" if v else "[FAIL]", k)
        raise RuntimeError(
            "V16E-0D blocked: recovered BL/DP source authority mismatch. "
            "Ensure the canonical recovered DP file is copied into the project root."
        )

    # -------------------------------------------------------------------------
    # Formal availability freeze
    # -------------------------------------------------------------------------

    freeze = {
        "milestone": "V16E-0D",
        "role":
            "Formal closure of legacy provenance recovery and architecture "
            "reconciliation before new prospective reproduction/integration.",

        "recovered_authorities": {
            "BL_physics_ladder_sources": {
                name: {
                    "path": rel(rec["path"]),
                    "sha256": rec["sha256"],
                    "status": "RECOVERED_EXACT_SOURCE",
                }
                for name, rec in BL_SOURCES.items()
            },
            "DP_8_layer_physics_source": {
                "path": rel(DP_SOURCE),
                "sha256": DP_SOURCE_SHA,
                "status": "RECOVERED_EXACT_SOURCE",
                "fingerprints": DP_MARKERS,
            },
        },

        "historical_learned_artifact_availability": {
            "BL_Round_1": {
                "status": "UNAVAILABLE_FOR_EXACT_PROVENANCE",
                "historical_definition": "earliest validated PI-RNN",
                "source_bound": False,
                "checkpoint_bound": False,
            },
            "BL_Round_2": {
                "status": "UNAVAILABLE_FOR_EXACT_PROVENANCE",
                "historical_definition": "expanded/conditioned PI-RNN",
                "source_bound": False,
                "checkpoint_bound": False,
            },
            "BL_Round_3": {
                "status": "UNAVAILABLE_FOR_EXACT_PROVENANCE",
                "historical_definition": "most complete BL PI-RNN",
                "source_bound": False,
                "checkpoint_bound": False,
            },
            "Hybrid_DP_PI_RNN_or_layer_RNN": {
                "status": "UNAVAILABLE_FOR_EXACT_PROVENANCE",
                "source_bound": False,
                "checkpoint_bound": False,
            },
        },

        "search_evidence": {
            "current_portable_project_searched": True,
            "sibling_PyCharm_projects_searched": True,
            "file_library_searched": True,
            "historical_learned_identity_recovery_complete": True,
        },

        "provenance_rule": {
            "may_call_future_model_historical_Round_1_2_3": False,
            "may_call_future_model_historical_Hybrid_DP": False,
            "may_retrain_from_exact_recovered_source": True,
            "future_retraining_label":
                "NEW V16E PROSPECTIVE REPRODUCTION — never historical checkpoint recovery",
            "new_checkpoint_requires_new_SHA_and_manifest": True,
            "new_training_requires_new_protocol": True,
        },

        "EXP_CS1_firewall": {
            "EXP_CS1_remains_closed": True,
            "geology0029_remains_consumed": True,
            "geology0029_may_not_be_new_unseen_test": True,
        },

        "WP0_state": {
            "common_transport_interface_frozen": True,
            "physics_authorities_frozen": True,
            "legacy_availability_audited": True,
            "WP0_complete": True,
        },

        "authorization": {
            "historical_checkpoint_deployment": False,
            "historical_round_claims": False,
            "prospective_source_reproduction_protocol_design": True,
            "TOF_adapter_design_from_exact_recovered_sources": True,
            "new_Hybrid_DP_design_from_exact_DP_physics": True,
            "training_now": False,
        },

        "execution_in_E0D": {
            "TensorFlow_import": False,
            "model_load": False,
            "checkpoint_load": False,
            "NPZ_load": False,
            "OOD_reopen": False,
            "training": False,
            "inference": False,
        },
    }

    FREEZE.write_text(json.dumps(freeze, indent=2))

    handoff = f"""# PAD-Stream V16E-0D — WP0 Closure and Prospective Reproduction Handoff

## 1. WP0 is complete

The architecture-reconciliation phase is now closed.

Exact recovered authorities:

- Stage 1 incompressible BL PI-RNN source:
  `{BL_SOURCES["Stage1_incompressible"]["sha256"]}`
- Stage 2 conservative compressible Godunov PI-RNN source:
  `{BL_SOURCES["Stage2_compressible_godunov"]["sha256"]}`
- Stage 3 capillary PI-RNN source:
  `{BL_SOURCES["Stage3_capillary"]["sha256"]}`
- Stage 4 full compressible-capillary Godunov PI-RNN source:
  `{BL_SOURCES["Stage4_full_compressible_capillary"]["sha256"]}`
- Canonical 8-layer DP physics source:
  `{DP_SOURCE_SHA}`

The common total-flow TOF interface and exact pressure/Darcy/Pollock authorities
remain frozen from V16E-0.

## 2. Historical learned artifacts are unavailable

After searching the portable project, sibling PyCharm projects, and the file
library, the exact historical learned identities remain unavailable for:

- BL Round 1 — earliest validated PI-RNN,
- BL Round 2 — expanded/conditioned PI-RNN,
- BL Round 3 — most complete BL PI-RNN,
- Hybrid DP PI-RNN / layer-RNN.

This is now a formal provenance statement, not an unresolved temporary guess.

## 3. Scientific consequence

The missing checkpoints do **not** invalidate the dissertation lineage.

They change how the next experiment is described.

We may reproduce/train models from the exact recovered Stage sources, but every
new trained artifact must be labeled as a **new V16E prospective reproduction**.

A new checkpoint may never be described as:

- the recovered historical Round 1 checkpoint,
- the recovered historical Round 2 checkpoint,
- the recovered historical Round 3 checkpoint,
- or the recovered historical Hybrid DP checkpoint.

## 4. Revised integration strategy

The next branch should proceed in this order:

### V16E-1A — BL source-reproduction protocol freeze

Before training:

- define which Stage source(s) are reproduced,
- bind original teacher/target semantics,
- define training/validation cases,
- define units and coordinate transformation to TOF,
- define acceptance metrics,
- assign new experiment IDs,
- define new checkpoint naming and SHA policy.

No geology0029 reuse as a new unseen test.

### V16E-1B — Reproduce original-coordinate BL models

Train new checkpoints from the exact recovered sources in their native
1-D coordinate systems first.

Goal:

`recovered source -> reproduced teacher agreement`

This establishes reproducibility without claiming historical-checkpoint recovery.

### V16E-1C — Total-flow TOF adapter

Only after native-coordinate reproduction passes:

`x / x_D formulation -> total-flow TOF interface`

The constitutive physics must remain unchanged.

Compressible and capillary branches require explicitly derived transformed
residuals rather than a blind coordinate substitution.

### V16E-2 — New Hybrid BL-DP branch

Use the recovered 8-layer DP physics source as the exact heterogeneity teacher:

- layer k/h/PV,
- rate allocation,
- local PVI,
- breakthrough ordering,
- flux-weighted aggregation.

If a learned Hybrid DP model is desired, it becomes a **new V16E model**
trained prospectively against this exact DP/BL teacher.

### V16E-3 — Compare with frozen PAD-Stream transport

Compare under identical path states:

- reproduced BL/TOF proposal,
- new Hybrid BL-DP proposal if built,
- frozen V16D/EXP-CS1 evidence baseline,
- exact numerical teacher.

Then choose the canonical proposal hierarchy from evidence.

## 5. Governing deployment rule remains unchanged

```text
learned proposal
      |
      v
physics residual / calibrated screen
      |
      +---- fail ---> exact teacher / fallback
      |
      v
bounded inventory correction
      |
      v
conservative path-to-grid map-back
      |
      v
accepted unique grid state
```

Pressure, Darcy flux, Pollock kinematics, inventory closure, and conservative
map-back remain physics authorities.

## 6. What is authorized now

Authorized:

- prospective BL reproduction protocol design,
- TOF adapter design from exact recovered BL sources,
- DP physics adapter/design using the recovered v14 source,
- new Hybrid BL-DP model design with a new experiment identity.

Not yet authorized:

- training before the new protocol is frozen,
- claiming any new checkpoint is a recovered historical Round checkpoint,
- reuse of geology0029 as a new unseen test.
"""

    HANDOFF.write_text(handoff, encoding="utf-8")

    final_gates = dict(gates)
    final_gates.update({
        "freeze_written_nonempty":
            FREEZE.exists() and FREEZE.stat().st_size > 0,
        "handoff_written_nonempty":
            HANDOFF.exists() and HANDOFF.stat().st_size > 0,

        "historical_Round1_frozen_unavailable": True,
        "historical_Round2_frozen_unavailable": True,
        "historical_Round3_frozen_unavailable": True,
        "historical_Hybrid_DP_frozen_unavailable": True,

        "no_substitute_called_historical": True,
        "new_reproduction_requires_new_identity": True,

        "WP0_complete": True,
        "prospective_reproduction_protocol_authorized": True,
        "training_not_yet_authorized": True,

        "EXP_CS1_remains_closed": True,
        "geology0029_remains_consumed": True,

        "no_TensorFlow_import": True,
        "no_model_load": True,
        "no_checkpoint_load": True,
        "no_NPZ_load": True,
        "no_OOD_reopen": True,
        "no_training": True,
        "no_inference": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16E_WP0_ARCHITECTURE_RECONCILIATION_COMPLETE_"
        "BL_AND_DP_PHYSICS_SOURCES_RECOVERED_"
        "HISTORICAL_LEARNED_ARTIFACTS_FROZEN_UNAVAILABLE_"
        "PROSPECTIVE_V16E_REPRODUCTION_PROTOCOL_AUTHORIZED_"
        "TRAINING_NOT_YET_AUTHORIZED"
        if ok
        else "V16E_E0D_WP0_CLOSURE_BLOCKED"
    )

    summary = {
        "milestone": "V16E-0D",
        "status": status,

        "freeze_sha256": sha256(FREEZE),
        "handoff_sha256": sha256(HANDOFF),

        "BL_Stage_sources_recovered": True,
        "DP_8_layer_physics_recovered": True,
        "DP_source_sha256": DP_SOURCE_SHA,

        "historical_Round_1_available": False,
        "historical_Round_2_available": False,
        "historical_Round_3_available": False,
        "historical_Hybrid_DP_available": False,

        "WP0_complete": True,
        "training_authorized": False,

        "next_milestone":
            "V16E-1A — Prospective BL source-reproduction protocol freeze "
            "(new experiment identities, native-coordinate teacher reproduction, "
            "TOF-adapter acceptance contract; no training yet)",

        "gates": {k: bool(v) for k, v in final_gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nAVAILABILITY FREEZE")
    print("  BL Stage 1-4 sources : RECOVERED / EXACT")
    print("  8-layer DP physics   : RECOVERED / EXACT")
    print("  Historical Round 1   : UNAVAILABLE")
    print("  Historical Round 2   : UNAVAILABLE")
    print("  Historical Round 3   : UNAVAILABLE")
    print("  Historical Hybrid DP : UNAVAILABLE")

    print("\nWP0")
    print("  architecture reconciliation : COMPLETE")
    print("  provenance recovery          : COMPLETE")
    print("  prospective reproduction     : AUTHORIZED")
    print("  training                      : NOT YET AUTHORIZED")

    print("\nFINAL GATES")
    for k, v in final_gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print(
        "  V16E-1A — Freeze prospective BL source-reproduction protocol "
        "before any new training."
    )

    print("\nFreeze SHA-256 :", sha256(FREEZE))
    print("Handoff SHA-256:", sha256(HANDOFF))
    print("Summary SHA-256:", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
