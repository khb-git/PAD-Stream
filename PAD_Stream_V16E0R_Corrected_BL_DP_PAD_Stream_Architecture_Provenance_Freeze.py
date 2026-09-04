#!/usr/bin/env python3
"""
PAD-Stream V16E-0R
Corrected BL / Dykstra-Parsons / PAD-Stream Architecture and Provenance Freeze

Scientific purpose
------------------
Correct the semantic interpretation of V16E architecture reconciliation using
the actual model lineage supplied by the researcher.

This milestone does NOT delete or rewrite V16E-0 / E0A / E0B / E0C. Those
remain immutable audit history. E0R supersedes only the incorrect interpretation
that the Buckley-Leverett lineage consisted of separate historical
"Round 1 / Round 2 / Round 3" model artifacts that needed recovery.

Authoritative corrected lineage
-------------------------------
Buckley-Leverett:
  * final incompressible PI-RNN source
  * final compressible PI-RNN source
  * final capillary PI-RNN source
  * final full compressible-capillary PI-RNN source

Dykstra-Parsons:
  * analytical/layered physics and 8-layer validation reference
  * 10-parameter Hybrid BL-DP PI-RNN integration
  * 12-parameter Hybrid BL-DP PI-RNN integration
  * synthetic N-layer formation generator

Important meanings
------------------
* The 8-layer DP case is a controlled validation/reference run, not an
  architectural restriction to eight layers.
* 10-param Hybrid:
    [no, nw, swc, sor, mu_w, mu_o, phi, tD, xD_star, Sw_star]
  with shared/fixed krw_max and kro_max.
* 12-param Hybrid:
    [no, nw, swc, sor, mu_w, mu_o, phi,
     krw_max, kro_max, tD, xD_star, Sw_star]
  with layer-specific relative-permeability endpoints.
* Absolute permeability k_md remains part of DP layer physics / kh allocation;
  it is NOT one of the 12 PI-RNN conditioning inputs.
* Saved trained weights/configs are currently unavailable. The source files are
  the authoritative final model definitions. Any future trained checkpoints are
  NEW V16E reproductions and require new manifests/hashes.
* Frozen V16D / EXP-CS1 remains a separate comparison baseline and is not
  modified or reopened.

NO TensorFlow import.
NO model/checkpoint load.
NO training.
NO inference.
NO NPZ load.
NO OOD reopening.
NO adapter implementation.
"""

from pathlib import Path
import hashlib
import json
import sys


R = Path(__file__).resolve().parent

OUT = R / "output" / "V16_E0R_CORRECTED_BL_DP_PAD_STREAM_ARCHITECTURE_FREEZE"
OUT.mkdir(parents=True, exist_ok=True)

CORRECTION = OUT / "V16E0R_Corrected_BL_DP_Model_Lineage_and_Provenance.json"
INTERFACE = OUT / "V16E0R_Corrected_Transport_Integration_Roles.json"
HANDOFF = OUT / "V16E0R_Revised_Development_Path.md"
SUMMARY = OUT / "PAD_Stream_V16E0R_Summary.json"


# =============================================================================
# Upstream audit history: V16E-0C
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


# E0D was drafted under the superseded interpretation and MUST remain unexecuted.
E0D_OUT = R / "output" / "V16_E0D_LEGACY_AVAILABILITY_FREEZE_AND_WP0_CLOSURE"
E0D_SUMMARY = E0D_OUT / "PAD_Stream_V16E0D_Summary.json"


# =============================================================================
# Exact authoritative source files
# =============================================================================

SOURCES = {
    "BL_FINAL_INCOMPRESSIBLE_PI_RNN": {
        "path": R / "pi_rnn_stage1_incompressible.py",
        "sha256": "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58",
        "role": "Final incompressible Buckley-Leverett PI-RNN source",
    },
    "BL_FINAL_COMPRESSIBLE_PI_RNN": {
        "path": R / "pi_rnn_stage2_compressible_godunov.py",
        "sha256": "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397",
        "role": "Final compressible conservative-Godunov Buckley-Leverett PI-RNN source",
    },
    "BL_FINAL_CAPILLARY_PI_RNN": {
        "path": R / "pi_rnn_stage3_capillary.py",
        "sha256": "dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f",
        "role": "Final capillary Buckley-Leverett PI-RNN source",
    },
    "BL_FINAL_FULL_PHYSICS_PI_RNN": {
        "path": R / "pi_rnn_stage4_full_godunov.py",
        "sha256": "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a",
        "role": "Final compressible-capillary Buckley-Leverett PI-RNN source",
    },

    "V14_DP_AND_STREAMLINE_PHYSICS": {
        "path": R / "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py",
        "sha256": "45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6",
        "role": "Validated V14 physics baseline including DP and streamline physics",
    },

    "DP_HYBRID_10_PARAM": {
        "path": R / "PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_10Param.py",
        "sha256": "2606f265d97ef1034a7555384daa79e4b3ddddef7c180b8d9f3fc3aedcc8d02f",
        "role": "10-parameter Hybrid BL-DP PI-RNN integration source",
    },
    "DP_HYBRID_12_PARAM": {
        "path": R / "PAD_Stream_Dykstra_Parsons_Hybrid_PIRNN_12Param.py",
        "sha256": "21116ddfd67f88585a0fc809075ece00008b09bd1f61536964ff03774ff8aae0",
        "role": "12-parameter Hybrid BL-DP PI-RNN integration source",
    },
    "DP_SYNTHETIC_GENERATOR": {
        "path": R / "PAD_Stream_Dykstra_Parsons_Synthetic_Formation_Generator.py",
        "sha256": "9f309f83d3b9d4f057641c545e050ead5e398a748d8aa24502059008336a65b9",
        "role": "Synthetic N-layer DP formation generator",
    },
}


# =============================================================================
# Source fingerprints
# =============================================================================

MARKERS = {
    "DP_HYBRID_10_PARAM": [
        "param_dim = 10",
        "p10 = np.array",
        "shared.krw_max",
        "shared.kro_max",
        "pi_rnn_fan_dp.weights.h5",
    ],
    "DP_HYBRID_12_PARAM": [
        "param_dim = 12",
        "krw_max",
        "kro_max",
        "pi_rnn_fan_dp_12param.weights.h5",
        "12-parameter",
    ],
    "DP_SYNTHETIC_GENERATOR": [
        "def calculate_vdp",
        "def generate_synthetic_formation",
        "n_layers",
        "k_md",
        "generate_homogeneous_formation",
        "generate_heterogeneous_formation",
    ],
    "V14_DP_AND_STREAMLINE_PHYSICS": [
        "class DykstraParsons",
        "Pollock",
        "time-of-flight",
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


def valid_sha(v: str) -> bool:
    return (
        isinstance(v, str)
        and len(v) == 64
        and all(c in "0123456789abcdef" for c in v.lower())
    )


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def marker_gates(path: Path, markers):
    if not path.exists():
        return {m: False for m in markers}
    txt = path.read_text(encoding="utf-8", errors="replace").lower()
    return {m: (m.lower() in txt) for m in markers}


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16E-0R")
    print("Corrected BL / Dykstra-Parsons / PAD-Stream Architecture Freeze")
    print("=" * 78)

    print(
        "\nCORRECTION / ARCHITECTURE ONLY — no TensorFlow, no model/checkpoint "
        "load, no NPZ, no OOD reopening, no training, no inference.\n"
    )

    if any(p.exists() for p in [CORRECTION, INTERFACE, HANDOFF, SUMMARY]):
        raise RuntimeError(
            "V16E-0R outputs already exist. Refusing to overwrite correction record."
        )

    gates = {
        "E0C_source_SHA_valid": valid_sha(E0C_SOURCE_SHA),
        "E0C_recovery_SHA_valid": valid_sha(E0C_RECOVERY_SHA),
        "E0C_round_audit_SHA_valid": valid_sha(E0C_ROUND_AUDIT_SHA),
        "E0C_summary_SHA_valid": valid_sha(E0C_SUMMARY_SHA),

        "E0C_source_SHA_exact": exact_sha(E0C_SOURCE, E0C_SOURCE_SHA),
        "E0C_recovery_SHA_exact": exact_sha(E0C_RECOVERY, E0C_RECOVERY_SHA),
        "E0C_round_audit_SHA_exact": exact_sha(E0C_ROUND_AUDIT, E0C_ROUND_AUDIT_SHA),
        "E0C_summary_SHA_exact": exact_sha(E0C_SUMMARY, E0C_SUMMARY_SHA),

        "superseded_E0D_not_executed": not E0D_SUMMARY.exists(),
    }

    print("UPSTREAM AUDIT GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-0R blocked: upstream audit mismatch or superseded E0D was executed."
        )

    e0c = read_json(E0C_SUMMARY)
    gates.update({
        "E0C_status_exact": e0c.get("status") == EXPECTED_E0C_STATUS,
        "E0C_adapter_coding_not_authorized":
            e0c.get("adapter_coding_authorized") is False,
    })

    for source_id, spec in SOURCES.items():
        gates[f"{source_id}_SHA_literal_valid"] = valid_sha(spec["sha256"])
        gates[f"{source_id}_SHA_exact"] = exact_sha(spec["path"], spec["sha256"])

    fingerprints = {}
    for source_id, markers in MARKERS.items():
        rec = marker_gates(SOURCES[source_id]["path"], markers)
        fingerprints[source_id] = rec
        for idx, (marker, passed) in enumerate(rec.items(), start=1):
            gates[f"{source_id}_semantic_marker_{idx:02d}"] = passed

    if not all(gates.values()):
        print("\nSOURCE / SEMANTIC GATES")
        for k, v in gates.items():
            print("[PASS]" if v else "[FAIL]", k)
        raise RuntimeError(
            "V16E-0R blocked: an authoritative source is missing, changed, "
            "or does not match the corrected scientific meaning."
        )

    source_record = {
        source_id: {
            "path": rel(spec["path"]),
            "sha256": spec["sha256"],
            "role": spec["role"],
            "status": "EXACT_SOURCE_BOUND",
        }
        for source_id, spec in SOURCES.items()
    }

    correction = {
        "milestone": "V16E-0R",
        "scientific_role":
            "Correct the semantic/provenance interpretation of V16E architecture "
            "reconciliation using the actual final BL and Hybrid DP model sources.",

        "audit_history_policy": {
            "V16E_0_E0A_E0B_E0C_deleted": False,
            "V16E_0_E0A_E0B_E0C_rewritten": False,
            "V16E_0_E0A_E0B_E0C_retained_as_audit_history": True,
            "superseded_interpretation":
                "The earlier search treated roadmap Round 1/2/3 labels as separate "
                "historical BL model artifacts. Researcher clarification establishes "
                "that the authoritative BL progression is the four final physics-phase "
                "PI-RNNs: incompressible, compressible, capillary, and full.",
            "E0D_draft_status": "OBSOLETE_UNEXECUTED_DO_NOT_RUN",
        },

        "authoritative_sources": source_record,
        "source_fingerprints": fingerprints,

        "corrected_BL_lineage": {
            "progression": [
                "final incompressible BL PI-RNN",
                "final compressible BL PI-RNN",
                "final capillary BL PI-RNN",
                "final full compressible-capillary BL PI-RNN",
            ],
            "Round_1_2_3_artifact_recovery_required": False,
            "meaning":
                "The four files are final models for successive physics phases, "
                "not temporary rounds requiring recovery.",
        },

        "corrected_DP_lineage": {
            "eight_layer_reference": {
                "role":
                    "Controlled validation case used to establish proper DP/layered physics, "
                    "flow allocation, breakthrough ordering, and composite behavior.",
                "architectural_layer_count_limit": False,
            },

            "Hybrid_10_param": {
                "conditioning_vector": [
                    "no", "nw", "swc", "sor", "mu_w", "mu_o", "phi",
                    "tD", "xD_star", "Sw_star",
                ],
                "param_dim": 10,
                "krw_max_kro_max":
                    "shared/fixed to match the PI-RNN training definition",
                "absolute_k_md_in_neural_conditioning": False,
                "absolute_k_md_role":
                    "DP layer physics / k*h flow allocation / heterogeneity",
            },

            "Hybrid_12_param": {
                "conditioning_vector": [
                    "no", "nw", "swc", "sor", "mu_w", "mu_o", "phi",
                    "krw_max", "kro_max", "tD", "xD_star", "Sw_star",
                ],
                "param_dim": 12,
                "relative_permeability_endpoints_conditioned": True,
                "absolute_k_md_in_neural_conditioning": False,
                "absolute_k_md_role":
                    "DP layer physics / k*h flow allocation / heterogeneity",
            },

            "synthetic_generator": {
                "arbitrary_N_layer_generation": True,
                "VDP_calculation": True,
                "formation_types": [
                    "homogeneous",
                    "heterogeneous",
                    "layered/thief-zone",
                ],
                "role":
                    "Expand testing beyond the 8-layer reference case before SGSim.",
            },
        },

        "checkpoint_availability": {
            "legacy_BL_saved_weights_currently_available": False,
            "legacy_Hybrid_DP_saved_weights_currently_available": False,
            "source_files_are_authoritative_model_definitions": True,
            "future_checkpoint_policy":
                "Any trained checkpoint created now is a NEW V16E reproduction "
                "with a new experiment ID, manifest, and SHA. It is not an old "
                "checkpoint recovery.",
        },

        "V16D_relationship": {
            "EXP_CS1_status": "CLOSED_FROZEN_COMPARISON_BASELINE",
            "geology0029_status": "CONSUMED_FINAL_TEST",
            "V16D_role":
                "Separate PAD-Stream recurrent Stage-4 transport baseline for "
                "later identical-state comparison.",
            "V16D_modified_in_E0R": False,
        },

        "firewall": {
            "TensorFlow_import": False,
            "checkpoint_load": False,
            "NPZ_load": False,
            "OOD_reopen": False,
            "training": False,
            "inference": False,
            "adapter_implementation": False,
        },
    }

    CORRECTION.write_text(json.dumps(correction, indent=2), encoding="utf-8")

    integration = {
        "milestone": "V16E-0R",

        "physics_authorities": {
            "pressure": "finite-volume pressure solve",
            "Darcy_flux": "conservative Darcy face fluxes",
            "trajectory": "exact Pollock streamline geometry",
            "transport_coordinate": "total-flow time of flight",
            "acceptance": [
                "transport physics residual / teacher agreement",
                "saturation bounds",
                "inventory closure",
                "conservative path-to-grid map-back",
            ],
        },

        "transport_research_lineages": {
            "BL_PI_RNN_lineage": [
                "incompressible",
                "compressible",
                "capillary",
                "full compressible-capillary",
            ],
            "Hybrid_DP_lineage": [
                "8-layer physics validation reference",
                "10-param Hybrid",
                "12-param Hybrid with relative-permeability endpoint conditioning",
                "synthetic N-layer heterogeneity",
            ],
            "PAD_Stream_lineage": [
                "SGSim geology",
                "finite-volume pressure",
                "conservative Darcy flux",
                "exact Pollock",
                "TOF",
                "frozen V16D recurrent Stage-4 comparison baseline",
            ],
        },

        "integration_question":
            "Can the validated physics-informed BL / Hybrid-DP transport lineage "
            "be expressed consistently on exact Pollock/TOF path states and improve "
            "or complement the frozen V16D recurrent transport proposal?",

        "canonical_transport_strategy": "DEFERRED_EVIDENCE_DRIVEN",

        "important_non_equivalences": [
            "DP is not SGSim spatial connectivity.",
            "8 layers is not a permanent architecture limit.",
            "krw_max/kro_max are relative-permeability endpoints, not absolute permeability.",
            "absolute permeability k_md is not one of the 12 neural conditioning variables.",
            "V16D recurrent transport is not the historical BL PI-RNN.",
            "a newly trained V16E checkpoint is not a recovered historical checkpoint.",
        ],
    }

    INTERFACE.write_text(json.dumps(integration, indent=2), encoding="utf-8")

    handoff = """# PAD-Stream V16E-0R — Corrected Development Path

## Status correction

V16E-0R supersedes the **interpretation**, not the files, of V16E-0A/B/C.

The prior provenance-search milestones remain immutable audit history. Their
assumption that the BL research lineage required recovery of separate historical
Round-1/2/3 artifacts is retired.

The actual Buckley-Leverett model lineage is:

1. Final incompressible PI-RNN
2. Final compressible PI-RNN
3. Final capillary PI-RNN
4. Final full compressible-capillary PI-RNN

Each source is the final model definition for that physics phase.

## Dykstra-Parsons lineage

The 8-layer case is a **controlled validation reference**, not the architecture.

The Hybrid lineage contains:

1. 10-parameter BL-DP PI-RNN
2. 12-parameter BL-DP PI-RNN
3. Synthetic N-layer DP formation generation

The 10-parameter conditioning vector is:

`[no, nw, swc, sor, mu_w, mu_o, phi, tD, xD_star, Sw_star]`

The 12-parameter conditioning vector is:

`[no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD_star, Sw_star]`

The additional variables are **relative-permeability endpoints**.

Absolute permeability `k_md` remains part of DP layer physics, `k*h` rate
allocation, and heterogeneity. It is not one of the 12 PI-RNN inputs.

## Saved weights

Historical trained weight/config files are currently unavailable.

Therefore:

- source code = authoritative final model definition;
- any model trained from these sources now = **new V16E reproduction**;
- every new reproduction requires a new experiment ID, manifest, checkpoint SHA,
  and validation record;
- no new reproduction may be described as recovery of an old checkpoint.

## Correct V16E sequence

### V16E-1A — BL reproduction protocol freeze

No training.

Freeze separately for the four final BL models:

- authoritative source SHA,
- native analytical/numerical teacher,
- training/validation semantics,
- input/conditioning vector,
- coordinate system,
- loss terms,
- expected checkpoint/config name for the new reproduction,
- deterministic seeds,
- acceptance metrics.

### V16E-1B — Native-coordinate BL reproduction

Retrain/reproduce the four final BL PI-RNNs in their original coordinate systems.

Compare:

- incompressible PI-RNN vs analytical BL,
- compressible PI-RNN vs conservative Godunov teacher,
- capillary PI-RNN vs capillary numerical teacher,
- full PI-RNN vs full compressible-capillary numerical teacher.

Do not transform to TOF yet.

### V16E-2 — BL-to-TOF transport transformation

Transform only after native reproduction is accepted.

The incompressible TOF form provides the simplest bridge.

Compressible/capillary/full residuals require explicit derivation; no blind
`x -> tau` substitution is allowed.

### V16E-3 — Hybrid DP reproduction and integration

Reproduce/test:

- 10-param Hybrid,
- 12-param Hybrid.

Use the 8-layer case as a controlled validation reference, then extend with the
synthetic generator.

### V16E-4 — Synthetic heterogeneity study

Exercise variable:

- layer count,
- DP severity,
- permeability distribution,
- thickness,
- porosity,
- Swc,
- relative-permeability endpoints,
- thief-zone structures.

This is the bridge from layered DP to full SGSim spatial heterogeneity.

### V16E-5 — Identical-state transport comparison

Under the same exact Pollock/TOF path states compare:

- exact/numerical transport teacher,
- validated BL PI-RNN / TOF branch,
- Hybrid BL-DP / TOF branch,
- frozen V16D recurrent Stage-4 baseline.

### V16E-6 — Evidence-driven transport strategy freeze

Choose only after V16E-5 whether PAD-Stream uses:

- one canonical proposal model,
- a physics-regime hierarchy,
- or multiple proposals with calibrated screen/fallback logic.

Pressure, Darcy, Pollock, inventory correction, and conservative map-back remain
physics authorities regardless of the learned transport proposal.

## Immediate next milestone

`V16E-1A — BL Native-Coordinate Reproduction Protocol Freeze`

This milestone defines the experiments but performs no training.
"""

    HANDOFF.write_text(handoff, encoding="utf-8")

    gates.update({
        "correction_written_nonempty":
            CORRECTION.exists() and CORRECTION.stat().st_size > 0,
        "integration_roles_written_nonempty":
            INTERFACE.exists() and INTERFACE.stat().st_size > 0,
        "handoff_written_nonempty":
            HANDOFF.exists() and HANDOFF.stat().st_size > 0,

        "Round_1_2_3_recovery_requirement_retired": True,
        "four_phase_BL_lineage_frozen": True,
        "eight_layer_DP_is_reference_not_limit": True,
        "Hybrid_10_param_bound": True,
        "Hybrid_12_param_bound": True,
        "relative_perm_endpoint_meaning_frozen": True,
        "absolute_k_not_12param_neural_input": True,
        "synthetic_N_layer_generator_bound": True,

        "legacy_weights_recorded_unavailable": True,
        "future_reproduction_requires_new_identity": True,

        "EXP_CS1_remains_closed": True,
        "geology0029_remains_consumed": True,

        "training_not_authorized_in_E0R": True,
        "adapter_not_implemented_in_E0R": True,
        "canonical_selector_deferred": True,

        "no_TensorFlow_import": True,
        "no_model_load": True,
        "no_checkpoint_load": True,
        "no_NPZ_load": True,
        "no_OOD_reopen": True,
        "no_training": True,
        "no_inference": True,
    })

    ok = bool(all(bool(v) for v in gates.values()))

    status = (
        "V16E_CORRECTED_BL_DP_PAD_STREAM_ARCHITECTURE_AND_PROVENANCE_FROZEN_"
        "FOUR_PHASE_BL_LINEAGE_CONFIRMED_"
        "HYBRID_10_AND_12_PARAM_DP_LINEAGE_CONFIRMED_"
        "EIGHT_LAYER_REFERENCE_NOT_ARCHITECTURE_LIMIT_"
        "LEGACY_WEIGHTS_UNAVAILABLE_NEW_REPRODUCTION_REQUIRED_"
        "V16E1A_PROTOCOL_FREEZE_AUTHORIZED_TRAINING_NOT_YET_AUTHORIZED"
        if ok else
        "V16E_E0R_CORRECTED_ARCHITECTURE_FREEZE_BLOCKED"
    )

    summary = {
        "milestone": "V16E-0R",
        "status": status,

        "correction_sha256": sha256(CORRECTION),
        "integration_roles_sha256": sha256(INTERFACE),
        "handoff_sha256": sha256(HANDOFF),

        "BL_final_model_count": 4,
        "Hybrid_DP_model_count": 2,
        "synthetic_DP_generator_bound": True,

        "legacy_BL_weights_available": False,
        "legacy_Hybrid_DP_weights_available": False,

        "Round_1_2_3_recovery_required": False,
        "E0D_obsolete": True,

        "next_milestone":
            "V16E-1A — BL Native-Coordinate Reproduction Protocol Freeze",
        "training_authorized": False,

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\nCORRECTED MODEL LINEAGE")
    print("  BL  : incompressible -> compressible -> capillary -> full")
    print("  DP  : 8-layer validation reference -> 10-param Hybrid -> "
          "12-param Hybrid -> synthetic N-layer")
    print("  k_md: DP physics / kh allocation, NOT 12-param neural conditioning")
    print("  krw_max/kro_max: added to 12-param neural conditioning")
    print("  saved historical weights: unavailable")
    print("  future training: new V16E reproduction identity required")

    print("\nAUDIT HISTORY")
    print("  E0 / E0A / E0B / E0C retained")
    print("  Round-1/2/3 recovery interpretation superseded")
    print("  E0D obsolete and must remain unexecuted")

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print("  V16E-1A — BL Native-Coordinate Reproduction Protocol Freeze")
    print("  Training remains NOT authorized.")

    print("\nCorrection SHA-256 :", sha256(CORRECTION))
    print("Roles SHA-256      :", sha256(INTERFACE))
    print("Handoff SHA-256    :", sha256(HANDOFF))
    print("Summary SHA-256    :", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
