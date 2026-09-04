#!/usr/bin/env python3
"""
PAD-Stream V16D-38
Master Version 16 Control-Space Branch Freeze + Development-Path Handoff

Purpose
-------
Freeze the completed V16D control-space / EXP-CS1 branch as an immutable
Version 16 development unit and produce a roadmap handoff for the next
PAD-Stream integration work.

This milestone is archival and architectural only.

It does NOT:
  * import TensorFlow,
  * load a model or checkpoint,
  * load NPZ arrays,
  * reopen geology0029,
  * run inference,
  * retrain,
  * tune,
  * change EXP-CS1,
  * reinterpret the OOD result.

The handoff distinguishes:
  A. what V16D has demonstrated,
  B. what V16D has NOT demonstrated,
  C. what remains to integrate in the revised PAD-Stream roadmap.
"""

from pathlib import Path
import hashlib
import json
import sys

R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_D38_MASTER_CONTROLSPACE_BRANCH_FREEZE_AND_DEVELOPMENT_HANDOFF"
)
OUT.mkdir(parents=True, exist_ok=True)

FREEZE = OUT / "V16D38_Master_ControlSpace_Branch_Freeze.json"
HANDOFF = OUT / "V16D38_PAD_Stream_Development_Path_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16D38_Summary.json"

# =============================================================================
# V16D-37-R3 FINAL PACKAGE AUTHORITY
# =============================================================================

D37R3_SOURCE = (
    R
    / "PAD_Stream_V16D37_R3_EXP_CS1_Final_Experiment_Package_Freeze_"
      "and_V16_Architecture_Theory_Integration_SHA_Correction.py"
)
D37R3_SOURCE_SHA = (
    "90c3471d66e194a6803f3a8af5156687f145c06de406a06aa72f9219b235ee3b"
)

D37R3_DIR = (
    R / "output"
    / "V16_D37_R3_EXP_CS1_FINAL_PACKAGE_AND_V16_THEORY_INTEGRATION_SHA_CORRECTION"
)

D37R3_MANIFEST = D37R3_DIR / "V16D37R3_EXP_CS1_Final_Experiment_Manifest.json"
D37R3_THEORY = D37R3_DIR / "V16D37R3_EXP_CS1_Architecture_Theory_Integration.md"
D37R3_SUMMARY = D37R3_DIR / "PAD_Stream_V16D37R3_Summary.json"

D37R3_MANIFEST_SHA = (
    "fdc294a4d454b8b5405e591e8fbffb3cc6d269b0be07a4204c5a968f278b99e1"
)
D37R3_THEORY_SHA = (
    "a83193b201bd694e5f536e612d355f8aa622ee4711ade13e18bdca2a6b0fbc14"
)
D37R3_SUMMARY_SHA = (
    "23d12e76e8ea4010a350b602388f9de598088257882a3d36516a33ae0cd0e3df"
)

EXPECTED_D37R3_STATUS = (
    "V16D_EXP_CS1_FINAL_EXPERIMENT_PACKAGE_SHA_CORRECTED_FROZEN_"
    "VERSION16_ARCHITECTURE_THEORY_INTEGRATED_EXPERIMENT_CLOSED"
)

# =============================================================================
# FINAL EXP-CS1 IDENTITIES
# =============================================================================

CHECKPOINT_SHA = (
    "dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13"
)
ARCHITECTURE_SHA = (
    "4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920"
)

OOD_RMSE = 4.235076137538e-03
OOD_MAE = 1.733692782761e-03
RMSE_OVER_VALIDATION = 0.972040
MAE_OVER_VALIDATION = 0.987730

CORRECT_D31D_SUMMARY_SHA = (
    "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3"
)


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
    return str(path.relative_to(R))


def main():
    print("=" * 78)
    print("PAD-Stream V16D-38")
    print("Master Control-Space Branch Freeze + Development-Path Handoff")
    print("=" * 78)

    print(
        "\nARCHIVAL / ROADMAP ONLY — no TensorFlow, no model load, no NPZ, "
        "no OOD reopening, no inference, no training, no tuning.\n"
    )

    if FREEZE.exists() or HANDOFF.exists() or SUMMARY.exists():
        raise RuntimeError(
            "D38 outputs already exist. Refusing to overwrite frozen handoff."
        )

    gates = {
        "D37R3_source_SHA_valid_64hex":
            valid_sha256_literal(D37R3_SOURCE_SHA),
        "D37R3_manifest_SHA_valid_64hex":
            valid_sha256_literal(D37R3_MANIFEST_SHA),
        "D37R3_theory_SHA_valid_64hex":
            valid_sha256_literal(D37R3_THEORY_SHA),
        "D37R3_summary_SHA_valid_64hex":
            valid_sha256_literal(D37R3_SUMMARY_SHA),
        "checkpoint_SHA_valid_64hex":
            valid_sha256_literal(CHECKPOINT_SHA),
        "architecture_SHA_valid_64hex":
            valid_sha256_literal(ARCHITECTURE_SHA),
        "D31D_summary_SHA_valid_64hex":
            valid_sha256_literal(CORRECT_D31D_SUMMARY_SHA),

        "D37R3_source_SHA_exact":
            exact_sha(D37R3_SOURCE, D37R3_SOURCE_SHA),
        "D37R3_manifest_SHA_exact":
            exact_sha(D37R3_MANIFEST, D37R3_MANIFEST_SHA),
        "D37R3_theory_SHA_exact":
            exact_sha(D37R3_THEORY, D37R3_THEORY_SHA),
        "D37R3_summary_SHA_exact":
            exact_sha(D37R3_SUMMARY, D37R3_SUMMARY_SHA),
    }

    print("MASTER FREEZE GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError("D38 blocked: D37-R3 final-package authority mismatch.")

    manifest = read_json(D37R3_MANIFEST)
    d37_summary = read_json(D37R3_SUMMARY)

    gates.update({
        "D37R3_status_exact":
            d37_summary.get("status") == EXPECTED_D37R3_STATUS,
        "EXP_CS1_closed":
            d37_summary.get("EXP_CS1_closed") is True,
        "geology0029_consumed":
            d37_summary.get("geology0029_consumed") is True,
        "checkpoint_SHA_exact":
            d37_summary.get("checkpoint_sha256") == CHECKPOINT_SHA,
        "architecture_SHA_exact":
            d37_summary.get("architecture_sha256") == ARCHITECTURE_SHA,
        "OOD_RMSE_exact":
            abs(float(d37_summary.get("OOD_RMSE")) - OOD_RMSE) < 5e-15,
        "OOD_MAE_exact":
            abs(float(d37_summary.get("OOD_MAE")) - OOD_MAE) < 5e-15,
        "RMSE_ratio_exact":
            abs(float(d37_summary.get("RMSE_over_validation"))
                - RMSE_OVER_VALIDATION) < 5e-7,
        "MAE_ratio_exact":
            abs(float(d37_summary.get("MAE_over_validation"))
                - MAE_OVER_VALIDATION) < 5e-7,
    })

    if not all(gates.values()):
        print("\nSEMANTIC GATES")
        for name, passed in gates.items():
            print("[PASS]" if passed else "[FAIL]", name)
        raise RuntimeError("D38 blocked: final EXP-CS1 semantic mismatch.")

    # -------------------------------------------------------------------------
    # Freeze the branch-level scientific interpretation.
    # -------------------------------------------------------------------------

    branch_freeze = {
        "milestone": "V16D-38",
        "branch": "V16D_CONTROLSPACE_EXP_CS1",
        "role":
            "Master immutable freeze of the completed Version 16D "
            "control-space recurrent Stage-4 branch.",

        "state": {
            "branch_complete": True,
            "EXP_CS1_closed": True,
            "geology0029_consumed_as_final_OOD": True,
            "further_EXP_CS1_tuning": "PROHIBITED",
            "new_learning_requires_new_independent_locked_test": True,
        },

        "final_authority": {
            "D37R3_source": {
                "path": rel(D37R3_SOURCE),
                "sha256": D37R3_SOURCE_SHA,
            },
            "D37R3_manifest": {
                "path": rel(D37R3_MANIFEST),
                "sha256": D37R3_MANIFEST_SHA,
            },
            "D37R3_theory": {
                "path": rel(D37R3_THEORY),
                "sha256": D37R3_THEORY_SHA,
            },
            "D37R3_summary": {
                "path": rel(D37R3_SUMMARY),
                "sha256": D37R3_SUMMARY_SHA,
            },
        },

        "frozen_model": {
            "experiment": "EXP-CS1",
            "architecture_sha256": ARCHITECTURE_SHA,
            "checkpoint_sha256": CHECKPOINT_SHA,
            "best_epoch": 73,
            "input_sequence_shape": [201, 9],
            "model":
                "LSTM64 -> LSTM64 -> TimeDistributed Dense(1,sigmoid) -> "
                "Rescaling[0.2,0.8]",
        },

        "scientific_firewall": {
            "TRAIN_geologies": ["0026", "0027"],
            "VALIDATION_geology": "0028",
            "LOCKED_OOD_geology": "0029",
            "controls": {
                "rates_tpd": [350, 500, 650],
                "producer_bhp_psi": [1800, 2000, 2200],
            },
            "generalization_unit":
                "complete Foundation Case = geology realization + rate/BHP pair",
            "D31D_summary_sha256": CORRECT_D31D_SUMMARY_SHA,
        },

        "final_OOD": {
            "MSE": 1.793586989075e-05,
            "RMSE": OOD_RMSE,
            "MAE": OOD_MAE,
            "RMSE_over_validation": RMSE_OVER_VALIDATION,
            "MAE_over_validation": MAE_OVER_VALIDATION,
            "interpretation":
                "Aggregate final-OOD RMSE and MAE are slightly below the "
                "frozen validation reference.",
        },

        "PAD_Stream_architecture_status": {
            "SGSim_heterogeneous_geology": "COMPLETE / FROZEN BASIS",
            "finite_volume_pressure": "PHYSICS AUTHORITY PRESENT",
            "conservative_Darcy_fluxes": "PHYSICS AUTHORITY PRESENT",
            "exact_Pollock_streamlines": "AUTHORITATIVE KINEMATICS",
            "TOF_transport_coordinates": "PRESENT",
            "control_space_recurrent_Stage4": "COMPLETE / FROZEN AS EXP-CS1",
            "ADV": "AUXILIARY",
            "FMM": "NOT EXP-CS1 PREDICTOR",
            "M_face": "PHYSICS SIDECAR NOT PREDICTOR",
        },

        "supported_claim": (
            "Within the frozen EXP-CS1 experiment, recurrent Stage-4 "
            "transport transfers from TRAIN geologies 0026-0027, through "
            "validation geology0028, to one independently locked unseen "
            "geology0029 across all nine rate/BHP controls without aggregate "
            "RMSE or MAE degradation relative to validation."
        ),

        "claim_boundary": (
            "The branch does not establish universal geological "
            "generalization across arbitrary reservoir realizations or field "
            "models."
        ),

        "execution_in_D38": {
            "TensorFlow_import": False,
            "model_load": False,
            "checkpoint_load": False,
            "NPZ_load": False,
            "OOD_reopen": False,
            "inference": False,
            "training": False,
            "tuning": False,
            "archival_and_roadmap_only": True,
        },
    }

    FREEZE.write_text(json.dumps(branch_freeze, indent=2))

    # -------------------------------------------------------------------------
    # Revised PAD-Stream development-path handoff.
    # -------------------------------------------------------------------------

    handoff = f"""# PAD-Stream V16D-38 — Master Branch Freeze and Development-Path Handoff

## 1. Decision

**The V16D control-space / EXP-CS1 branch is complete and should be frozen.**

There is no scientific reason to continue tuning EXP-CS1. The final
geology0029 OOD set has already been consumed, and the final model performed
without aggregate validation degradation:

- OOD RMSE = **{OOD_RMSE:.12e}**
- OOD MAE = **{OOD_MAE:.12e}**
- OOD RMSE / validation RMSE = **{RMSE_OVER_VALIDATION:.6f}**
- OOD MAE / validation MAE = **{MAE_OVER_VALIDATION:.6f}**

The next work should therefore extend the PAD-Stream architecture rather than
revisit this experiment.

---

## 2. What V16D completed

V16D established a controlled heterogeneous SGSim learning experiment around
the Stage-4 transport component.

### Frozen physical backbone

**SGSim geology -> finite-volume pressure -> conservative Darcy fluxes ->
exact Pollock streamlines -> TOF/transport coordinates**

This backbone remains physics-defined.

### Frozen recurrent transport experiment

EXP-CS1 uses a 201-node, nine-channel streamline sequence and a two-layer
LSTM transport predictor.

It has been tested across:

- TRAIN geology realizations 0026 and 0027,
- VALIDATION geology0028,
- independent locked-OOD geology0029,
- injection rates 350 / 500 / 650 t/day,
- producer BHP 1800 / 2000 / 2200 psi.

The final unseen-geology result is slightly better in aggregate than the
frozen validation reference.

---

## 3. What should NOT be done next

The following paths are closed under EXP-CS1:

- retraining EXP-CS1,
- trying another EXP-CS1 checkpoint on geology0029,
- changing the nine predictor channels and retesting geology0029,
- changing normalization and retesting geology0029,
- introducing a new loss or threshold and using geology0029 to judge it,
- treating geology0029 as unseen in a later experiment.

Any new learning experiment needs a new prospectively locked test realization.

---

## 4. Remaining revised PAD-Stream development path

### Next integration branch — BL / Hybrid DP transport integration

The next architectural task should be to integrate the previously developed:

1. **Buckley-Leverett PI-RNN transport formulation**, and
2. **Hybrid Dykstra-Parsons PI-RNN heterogeneity formulation**

into the frozen PAD-Stream streamline transport architecture.

This should be treated as a **new integration branch**, not a modification of
EXP-CS1.

Recommended goals:

- preserve Pollock as authoritative kinematics,
- preserve exact pressure / Darcy physics,
- preserve the V16D frozen control-space branch as comparison evidence,
- define how BL physics-informed transport and DP heterogeneity conditioning
  enter the Stage-4 transport layer,
- distinguish learned transport physics from geological-state descriptors,
- prospectively define any new TRAIN / VALIDATION / LOCKED-OOD split before
  evaluating the new learning formulation.

### After BL / DP integration — IBDP field-transfer branch

Once the revised PAD-Stream architecture is integrated and frozen, proceed to
the IBDP work as the larger field-model transfer stage.

The IBDP branch should be treated as a new scale/geometry/domain-transfer
problem rather than as another iteration of EXP-CS1.

---

## 5. Recommended milestone sequence

### V16E-0 — BL / DP Integration Contract
Freeze the role of:
- BL PI-RNN,
- Hybrid DP PI-RNN,
- Pollock,
- pressure / Darcy physics,
- Stage-4 transport coordinates,
- recurrent/global state components.

No training.

### V16E-1 — Frozen BL Transport Adapter
Connect the previously validated BL PI-RNN formulation to the 201-node
streamline transport interface without changing the frozen V16D evidence.

### V16E-2 — Frozen Hybrid DP Heterogeneity Adapter
Introduce the DP hybrid heterogeneity representation explicitly and define
where it conditions transport.

### V16E-3 — Integrated BL+DP Stage-4 Experiment Contract
Define new datasets, split firewall, normalization, losses, metrics, and new
locked test identity before training.

### V16E-4+ — Train / Validate / One-Touch Test
Execute the new integrated transport experiment prospectively.

### V16F — Full PAD-Stream Architecture Freeze
Freeze the complete revised architecture after BL/DP integration.

### Field-transfer branch — IBDP
Move the frozen architecture to the IBDP geological/reservoir model.

---

## 6. Architecture after V16D

```text
SGSim geology
      |
      v
Finite-volume pressure
      |
      v
Conservative Darcy fluxes
      |
      v
Exact 3-D Pollock streamlines
      |
      v
TOF / transport coordinates
      |
      +-----------------------------+
      |                             |
      v                             v
Frozen EXP-CS1 evidence       Next V16E integration
(control-space recurrent)     BL PI-RNN + Hybrid DP PI-RNN
      |                             |
      +-------------+---------------+
                    |
                    v
        Integrated Stage-4 transport
                    |
                    v
        Conservative map-back / state
                    |
                    v
        Global recurrent PAD-Stream
                    |
                    v
              IBDP transfer
```

---

## 7. Scientific interpretation of where we are

The important shift after V16D is that **heterogeneous SGSim transport
generalization is no longer an untested architecture idea**. It now has a
prospectively separated TRAIN / VALIDATION / locked-OOD experiment behind it.

The next dissertation-development question is therefore no longer:

> Can a recurrent Stage-4 transport model work on the heterogeneous SGSim
> PAD-Stream representation?

V16D provides evidence that it can within the frozen experiment.

The next question becomes:

> How do the previously developed Buckley-Leverett physics-informed transport
> and Hybrid Dykstra-Parsons heterogeneity formulations become explicit,
> integrated components of the full PAD-Stream architecture?

That is the natural handoff into V16E.
"""

    HANDOFF.write_text(handoff, encoding="utf-8")

    final_gates = dict(gates)
    final_gates.update({
        "freeze_written_nonempty":
            FREEZE.exists() and FREEZE.stat().st_size > 0,
        "handoff_written_nonempty":
            HANDOFF.exists() and HANDOFF.stat().st_size > 0,

        "D37R3_manifest_unchanged":
            sha256(D37R3_MANIFEST) == D37R3_MANIFEST_SHA,
        "D37R3_theory_unchanged":
            sha256(D37R3_THEORY) == D37R3_THEORY_SHA,
        "D37R3_summary_unchanged":
            sha256(D37R3_SUMMARY) == D37R3_SUMMARY_SHA,

        "EXP_CS1_not_reopened": True,
        "EXP_CS1_not_retrained": True,
        "EXP_CS1_not_retuned": True,
        "V16D_branch_frozen": True,
        "next_branch_is_new_integration_branch": True,
        "roadmap_handoff_complete": True,
    })

    ok = bool(all(bool(v) for v in final_gates.values()))

    status = (
        "V16D_MASTER_CONTROLSPACE_BRANCH_FROZEN_"
        "DEVELOPMENT_PATH_HANDOFF_COMPLETE_V16E_INTEGRATION_AUTHORIZED"
        if ok
        else "V16D_D38_MASTER_BRANCH_FREEZE_BLOCKED"
    )

    summary = {
        "milestone": "V16D-38",
        "status": status,
        "branch": "V16D_CONTROLSPACE_EXP_CS1",
        "EXP_CS1_closed": True,
        "geology0029_consumed": True,
        "V16D_branch_frozen": bool(ok),

        "freeze_sha256": sha256(FREEZE),
        "handoff_sha256": sha256(HANDOFF),

        "D37R3_manifest_sha256": D37R3_MANIFEST_SHA,
        "D37R3_theory_sha256": D37R3_THEORY_SHA,
        "D37R3_summary_sha256": D37R3_SUMMARY_SHA,

        "next_branch": "V16E",
        "next_milestone":
            "V16E-0 — Freeze BL PI-RNN + Hybrid DP PI-RNN integration "
            "contract within the revised PAD-Stream Stage-4 architecture",

        "gates": {k: bool(v) for k, v in final_gates.items()},
    }

    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("\nBRANCH ASSESSMENT")
    print("  V16D / EXP-CS1 : COMPLETE / CLOSED / FROZEN")
    print("  geology0029     : CONSUMED FINAL OOD TEST")
    print("  further tuning  : PROHIBITED")
    print("  next branch     : V16E — BL PI-RNN + Hybrid DP integration")

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nNEXT")
    print(
        "  V16E-0 — Freeze BL PI-RNN + Hybrid DP PI-RNN integration "
        "contract within revised PAD-Stream."
    )

    print("\nFreeze SHA-256 :", sha256(FREEZE))
    print("Handoff SHA-256:", sha256(HANDOFF))
    print("Summary SHA-256:", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
