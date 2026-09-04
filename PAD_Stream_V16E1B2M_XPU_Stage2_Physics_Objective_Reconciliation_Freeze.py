#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2M-XPU
Compressible Stage-2 Physics-Objective Reconciliation Freeze

Purpose
-------
Freeze the scientific interpretation of the completed Stage-2 investigation
after B2L demonstrated that the frozen conservative Godunov teacher itself
strongly violates the retained characteristic residual for Nc > 0.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Key finding
-----------
Frozen Stage-2 teacher:
    dS/dt_D + d[u_D f_w(S)]/dx_D = 0
    u_D = exp(Nc*x_D)

Frozen retained characteristic residual:
    R_char = y(xi*xD_star;Nc) - t_D * df_w/dS

with:
    y(x;Nc) = -expm1(-Nc*x)/Nc
    Nc -> 0 : y -> x

The conservative PDE expands as:
    dS/dt_D
    + u_D * df_w/dS * dS/dx_D
    + Nc * u_D * f_w
    = 0

The last term vanishes only at Nc=0. Therefore the retained simple
characteristic relation is not the complete conservative compressible PDE
constraint for Nc>0.

B2L measured this incompatibility directly on the frozen Godunov truth:
teacher characteristic-physics MSE increased by ~49x between Nc=0 and Nc=0.30
on the frozen holdout split.

Stage-2 branch roles frozen here
--------------------------------
1. SOURCE-FAITHFUL / HISTORICAL LINEAGE
   Preserve the original Stage-2 source and all reproduction artifacts exactly.
   Do not rewrite history or claim the characteristic residual is the exact
   conservative Godunov residual.

2. BEST-ACCURACY EXPERIMENTAL BRANCH
   Preserve COMP-XPU-004 (xi + eta) because B2K shows the best absolute
   reproduction accuracy so far and mostly improved Nc response behavior.
   Do NOT label its characteristic physics loss as a conservative-PDE residual.

3. CORRECTED CONSERVATIVE PI-RNN BRANCH
   No training is authorized yet.
   Before a new model is trained, derive the conservative residual consistently
   in the model's moving fan-coordinate representation. In particular, the
   model conditions on tD, xD_star and Sw_star and uses xi=xD/xD_star, so a
   direct physical-space PDE residual requires the appropriate chain rule and
   treatment of the moving xD_star(tD) coordinate.

B3 remains blocked until that residual-design question is resolved OR a later
explicit closure milestone elects to proceed with the source-faithful Stage-2
model while carrying this incompatibility as a documented limitation.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import sys


R = Path(__file__).resolve().parent

OUT = (
    R / "output"
    / "V16_E1B2M_XPU_STAGE2_PHYSICS_OBJECTIVE_RECONCILIATION_FREEZE"
)
OUT.mkdir(parents=True, exist_ok=True)

INTERPRETATION = OUT / "V16E1B2M_Stage2_Physics_Objective_Reconciliation.json"
BRANCHES = OUT / "V16E1B2M_Stage2_Branch_Roles.json"
HANDOFF = OUT / "V16E1B2M_Conservative_Residual_Design_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2M_XPU_Summary.json"

# ---------------------------------------------------------------------
# Frozen Stage-2 source
# ---------------------------------------------------------------------

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

# ---------------------------------------------------------------------
# B2K comparison
# ---------------------------------------------------------------------

B2K_SOURCE = (
    R
    / "PAD_Stream_V16E1B2K_XPU_COMP_XPU_002_vs_004_Physics_Aware_Eta_Comparison.py"
)
B2K_SOURCE_SHA = "a265d772dbe93ecd4d7079526fe7d9cc441d21f723cb6dd47f825a2f8e1a5f80"

B2K_DIR = (
    R / "output"
    / "V16_E1B2K_XPU_COMPRESSIBLE_COMP002_vs_COMP004_COMPARISON"
)
B2K_COMPARISON = B2K_DIR / "V16E1B2K_COMP_XPU_002_vs_004_Comparison.json"
B2K_SUMMARY = B2K_DIR / "PAD_Stream_V16E1B2K_XPU_Summary.json"

B2K_COMPARISON_SHA = "68e5f8853d991219e205bd98f757ab25ebeca1d8b957313943fdee86f7b3c755"
B2K_SUMMARY_SHA = "2a25b4779455a87ae2cf2e1810f2cb93d5116958470f69d374a095e218fdcac0"

EXPECTED_B2K_STATUS = (
    "V16E1B2K_XPU_COMP_XPU_002_VS_004_PHYSICS_AWARE_ETA_CHANNEL_COMPARISON_COMPLETE_"
    "OVERALL_PER_NC_HOLDOUT_PER_NC_LOSSES_FULL_DOMAIN_FRONT_EXCLUDED_FRONT_POSITION_"
    "MODEL_TO_TEACHER_RESPONSE_GAINS_AND_NC_RESPONSE_RATIOS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "B3_DECISION_REQUIRES_INTERPRETATION"
)

# ---------------------------------------------------------------------
# B2L teacher/residual compatibility audit
# ---------------------------------------------------------------------

B2L_SOURCE = (
    R
    / "PAD_Stream_V16E1B2L_XPU_Godunov_Teacher_Characteristic_Residual_Compatibility_Audit.py"
)
B2L_SOURCE_SHA = "a4ccf8e40988c3ec10bd49aa167a9cb674c567ede32418d66fa4d7241c8ad8e5"

B2L_DIR = (
    R / "output"
    / "V16_E1B2L_XPU_GODUNOV_TEACHER_CHARACTERISTIC_RESIDUAL_AUDIT"
)
B2L_AUDIT = B2L_DIR / "V16E1B2L_Godunov_Teacher_Characteristic_Residual_Audit.json"
B2L_SUMMARY = B2L_DIR / "PAD_Stream_V16E1B2L_XPU_Summary.json"

B2L_AUDIT_SHA = "341b7e063fbaa76bac1c59e941765da250a9cc7ee7ff3a3bd6856ca04ffce515"
B2L_SUMMARY_SHA = "9526536d21986e533850c00697142af14ca8804d1b9ccf0de812e92c276f3b34"

EXPECTED_B2L_STATUS = (
    "V16E1B2L_XPU_GODUNOV_TEACHER_CHARACTERISTIC_RESIDUAL_COMPATIBILITY_AUDIT_COMPLETE_"
    "PER_NC_TRAIN_AND_HOLDOUT_TEACHER_PHYSICS_LOSSES_AND_MODEL_VS_TEACHER_RESIDUAL_GAPS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "STAGE2_CLOSURE_AND_B3_DECISION_REQUIRE_INTERPRETATION"
)

# ---------------------------------------------------------------------
# Important immutable model identities
# ---------------------------------------------------------------------

COMP002_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)
COMP002_CHECKPOINT = COMP002_DIR / "V16E_BLREP_COMP_XPU_002.pt"
COMP002_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"

COMP004_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-004"
)
COMP004_CHECKPOINT = COMP004_DIR / "V16E_BLREP_COMP_XPU_004.pt"
COMP004_CHECKPOINT_SHA = "2b54c6ace6c893916bf55ee54dea2ad55eb3b5239d8e0c0cda21bc9311efca69"
COMP004_MANIFEST = COMP004_DIR / "V16E_BLREP_COMP_XPU_004_Manifest.json"
COMP004_MANIFEST_SHA = "989d3aaca374b44a9f6f9d0a35b9b0ddf8a86b3665e5b58f9bbb4f97ad08add7"
COMP004_SUMMARY = COMP004_DIR / "PAD_Stream_V16E1B2J_XPU_Summary.json"
COMP004_SUMMARY_SHA = "d4fc1de7a0257be90f2629e7e1469a30f2e7011d5586e32799f9c2f7338658b0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finite(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2M-XPU")
    print("Compressible Stage-2 Physics-Objective Reconciliation Freeze")
    print("=" * 80)
    print("RECONCILIATION ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2M summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),

        "B2K_source_SHA_exact":
            exact(B2K_SOURCE, B2K_SOURCE_SHA),
        "B2K_comparison_SHA_exact":
            exact(B2K_COMPARISON, B2K_COMPARISON_SHA),
        "B2K_summary_SHA_exact":
            exact(B2K_SUMMARY, B2K_SUMMARY_SHA),

        "B2L_source_SHA_exact":
            exact(B2L_SOURCE, B2L_SOURCE_SHA),
        "B2L_audit_SHA_exact":
            exact(B2L_AUDIT, B2L_AUDIT_SHA),
        "B2L_summary_SHA_exact":
            exact(B2L_SUMMARY, B2L_SUMMARY_SHA),

        "COMP002_checkpoint_SHA_exact":
            exact(COMP002_CHECKPOINT, COMP002_CHECKPOINT_SHA),

        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "COMP004_manifest_SHA_exact":
            exact(COMP004_MANIFEST, COMP004_MANIFEST_SHA),
        "COMP004_summary_SHA_exact":
            exact(COMP004_SUMMARY, COMP004_SUMMARY_SHA),
    }

    b2k = read_json(B2K_SUMMARY) if B2K_SUMMARY.exists() else {}
    b2l_summary = read_json(B2L_SUMMARY) if B2L_SUMMARY.exists() else {}
    audit = read_json(B2L_AUDIT) if B2L_AUDIT.exists() else {}

    gates.update({
        "B2K_status_exact":
            b2k.get("status") == EXPECTED_B2K_STATUS,

        "B2K_B3_false":
            b2k.get("B3_authorized") is False,

        "B2L_status_exact":
            b2l_summary.get("status") == EXPECTED_B2L_STATUS,

        "B2L_B3_false":
            b2l_summary.get("B3_authorized") is False,

        "B2L_closure_interpretation_required":
            b2l_summary.get("Stage2_closure_requires_interpretation") is True,
    })

    teacher_holdout = (
        audit.get(
            "teacher_characteristic_physics_loss",
            {},
        ).get(
            "holdout",
            {},
        )
    )

    compatibility = audit.get(
        "model_vs_teacher_compatibility",
        {},
    )

    ratio_block = audit.get(
        "Nc030_over_Nc000_physics_loss_ratios",
        {},
    )

    expected_nc = {"0.00", "0.05", "0.10", "0.20", "0.30"}

    gates.update({
        "teacher_holdout_all_Nc_present":
            set(teacher_holdout.keys()) == expected_nc,

        "teacher_holdout_all_finite":
            all(
                finite(
                    rec.get(
                        "teacher_characteristic_physics_mse"
                    )
                )
                for rec in teacher_holdout.values()
            ),

        "compatibility_all_Nc_present":
            set(compatibility.keys()) == expected_nc,

        "teacher_ratio_finite":
            finite(
                ratio_block.get(
                    "Godunov_teacher_holdout"
                )
            ),

        "teacher_ratio_gt_model002_ratio":
            float(
                ratio_block[
                    "Godunov_teacher_holdout"
                ]
            )
            >
            float(
                ratio_block[
                    "COMP_XPU_002_holdout"
                ]
            ),

        "teacher_ratio_gt_model004_ratio":
            float(
                ratio_block[
                    "Godunov_teacher_holdout"
                ]
            )
            >
            float(
                ratio_block[
                    "COMP_XPU_004_holdout"
                ]
            ),
    })

    # At every positive Nc, frozen teacher characteristic residual exceeds both
    # model residuals. This is an observed relation, not an invented threshold.
    positive_nc = ["0.05", "0.10", "0.20", "0.30"]

    gates.update({
        "positive_Nc_teacher_residual_exceeds_COMP002":
            all(
                float(
                    compatibility[nc][
                        "teacher_characteristic_physics_mse"
                    ]
                )
                >
                float(
                    compatibility[nc][
                        "COMP_XPU_002_physics_mse"
                    ]
                )
                for nc in positive_nc
            ),

        "positive_Nc_teacher_residual_exceeds_COMP004":
            all(
                float(
                    compatibility[nc][
                        "teacher_characteristic_physics_mse"
                    ]
                )
                >
                float(
                    compatibility[nc][
                        "COMP_XPU_004_physics_mse"
                    ]
                )
                for nc in positive_nc
            ),
    })

    # B2K observed COMP004 as better overall absolute reproduction.
    gates.update({
        "COMP004_overall_RMSE_improved":
            float(
                b2k[
                    "overall_RMSE_percent_improvement"
                ]
            )
            > 0.0,

        "COMP004_overall_MAE_improved":
            float(
                b2k[
                    "overall_MAE_percent_improvement"
                ]
            )
            > 0.0,
    })

    print("AUTHORITY / RECONCILIATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2M reconciliation freeze blocked by authority/evidence gate."
        )

    interpretation = {
        "milestone":
            "V16E-1B2M-XPU",

        "classification":
            "STAGE2_PHYSICS_OBJECTIVE_RECONCILIATION",

        "frozen_evidence": {
            "B2K_comparison_sha256":
                B2K_COMPARISON_SHA,

            "B2L_audit_sha256":
                B2L_AUDIT_SHA,

            "Godunov_teacher_holdout_Nc030_over_Nc000_characteristic_physics_ratio":
                ratio_block[
                    "Godunov_teacher_holdout"
                ],

            "COMP_XPU_002_holdout_Nc030_over_Nc000_characteristic_physics_ratio":
                ratio_block[
                    "COMP_XPU_002_holdout"
                ],

            "COMP_XPU_004_holdout_Nc030_over_Nc000_characteristic_physics_ratio":
                ratio_block[
                    "COMP_XPU_004_holdout"
                ],

            "COMP_XPU_004_overall_RMSE_percent_improvement_vs_COMP002":
                b2k[
                    "overall_RMSE_percent_improvement"
                ],

            "COMP_XPU_004_overall_MAE_percent_improvement_vs_COMP002":
                b2k[
                    "overall_MAE_percent_improvement"
                ],
        },

        "equation_reconciliation": {
            "conservative_teacher":
                "dS/dtD + d[uD*f_w(S)]/dxD = 0, uD=exp(Nc*xD)",

            "expanded_conservative_teacher":
                "dS/dtD + uD*f_w'(S)*dS/dxD + Nc*uD*f_w(S) = 0",

            "retained_characteristic_constraint":
                "y(xi*xD_star;Nc) - tD*f_w'(S) = 0",

            "missing_conservative_term_relative_to_simple_characteristic_relation":
                "Nc*uD*f_w(S)",

            "Nc0_limit":
                "The additional conservative term vanishes at Nc=0, consistent "
                "with exact Stage-1 nesting of the retained characteristic residual.",
        },

        "scientific_interpretation":
            "B2L demonstrates that the conservative Godunov target and retained "
            "simple characteristic residual are not mutually zero-residual "
            "objectives for Nc>0. The large positive-Nc teacher residual is a "
            "property of the frozen objective pair, not solely a neural-network "
            "approximation failure. Therefore a model's larger characteristic "
            "physics loss at high Nc cannot by itself be interpreted as worse "
            "agreement with the conservative governing equation.",

        "COMP004_interpretation":
            "COMP-XPU-004 is preserved as the best absolute reproduction branch "
            "observed so far. Its high-Nc characteristic physics loss must be "
            "interpreted relative to the incompatible teacher/residual pair and "
            "must not be mislabeled as a direct conservative-PDE residual.",

        "prohibited_conclusions": [
            "COMP-XPU-004 is less physical simply because its high-Nc characteristic loss is larger",
            "the Godunov teacher is wrong",
            "the original Stage-2 source should be overwritten",
            "a new arbitrary Nc loss multiplier is scientifically justified",
            "B3 is automatically authorized",
        ],
    }

    INTERPRETATION.write_text(
        json.dumps(
            interpretation,
            indent=2,
        ),
        encoding="utf-8",
    )

    branches = {
        "milestone":
            "V16E-1B2M-XPU",

        "source_faithful_historical_lineage": {
            "status":
                "PRESERVED",

            "authority":
                "pi_rnn_stage2_compressible_godunov.py",

            "source_sha256":
                STAGE2_SHA,

            "rule":
                "Never rewrite the original Stage-2 source definition or "
                "retroactively describe its characteristic residual as the "
                "exact conservative Godunov PDE residual.",

            "role":
                "Historical/source-definition provenance and reproduction lineage.",
        },

        "best_accuracy_experimental_branch": {
            "status":
                "PRESERVED",

            "experiment":
                "V16E-BLREP-COMP-XPU-004",

            "checkpoint_sha256":
                COMP004_CHECKPOINT_SHA,

            "architecture":
                "[xi, eta] sequence features + raw physical 11-D p11",

            "role":
                "Best observed absolute Stage-2 reproduction candidate pending "
                "final closure decision.",

            "limitation":
                "Still trained with the retained characteristic residual, which "
                "B2L shows is incompatible with the conservative Godunov teacher "
                "for Nc>0.",
        },

        "corrected_conservative_PI_RNN_branch": {
            "status":
                "DESIGN_REQUIRED_BEFORE_TRAINING",

            "training_authorized":
                False,

            "required_next_work":
                "Derive a conservative residual consistent with the moving fan "
                "coordinate xi=xD/xD_star(tD) and the model conditioner.",

            "do_not_assume":
                [
                    "that dS/dtD at fixed xi equals dS/dtD at fixed xD",
                    "that xD_star is constant with time",
                    "that the simple characteristic residual can be repaired by a scalar weight",
                ],

            "candidate_physical_equation":
                "dS/dtD + d[uD*f_w(S)]/dxD = 0",

            "coordinate_transform_requirement":
                "Apply the chain rule consistently before implementing the residual "
                "in xi/tD coordinates.",
        },
    }

    BRANCHES.write_text(
        json.dumps(
            branches,
            indent=2,
        ),
        encoding="utf-8",
    )

    handoff = (
        "# V16E-1B2M-XPU — Conservative Residual Design Handoff\n\n"
        "## Frozen conclusion\n\n"
        "The Stage-2 conservative Godunov teacher and retained simple characteristic "
        "residual are objectively incompatible for positive Nc. B2L measured the "
        "teacher's own characteristic residual directly, and the positive-Nc values "
        "are far larger than those of either trained model.\n\n"
        "## Do not launch another Stage-2 training experiment yet\n\n"
        "The next scientific task is a coordinate derivation, not hyperparameter "
        "tuning.\n\n"
        "Start from the physical conservative equation:\n\n"
        "    dS/dtD + d[uD f_w(S)]/dxD = 0\n"
        "    uD = exp(Nc*xD)\n\n"
        "or expanded:\n\n"
        "    dS/dtD + uD f_w'(S) dS/dxD + Nc uD f_w(S) = 0\n\n"
        "The recurrent fan model uses:\n\n"
        "    xi = xD / xD_star(tD)\n\n"
        "so the time derivative at fixed physical xD is not generally the same "
        "as the time derivative at fixed xi. The next milestone must derive that "
        "chain rule and decide how xD_star(tD) is represented before any corrected "
        "conservative residual is coded.\n\n"
        "## Branch preservation\n\n"
        "* Preserve source-faithful Stage-2 lineage unchanged.\n"
        "* Preserve COMP-XPU-004 checkpoint unchanged as the best current accuracy branch.\n"
        "* Do not authorize B3 until a later explicit closure decision.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    gates.update({
        "interpretation_written":
            INTERPRETATION.exists()
            and INTERPRETATION.stat().st_size > 0,

        "branch_roles_written":
            BRANCHES.exists()
            and BRANCHES.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "source_faithful_lineage_preserved":
            True,

        "COMP004_preserved":
            True,

        "corrected_residual_training_not_authorized":
            True,

        "B3_not_authorized":
            True,

        "no_training":
            True,

        "no_optimizer":
            True,

        "no_weight_update":
            True,

        "no_OOD":
            True,

        "no_TOF":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2M_XPU_STAGE2_PHYSICS_OBJECTIVE_RECONCILIATION_FROZEN_"
        "CONSERVATIVE_GODUNOV_TEACHER_AND_RETAINED_CHARACTERISTIC_RESIDUAL_INCOMPATIBILITY_CONFIRMED_FOR_POSITIVE_NC_"
        "SOURCE_FAITHFUL_STAGE2_LINEAGE_PRESERVED_COMP_XPU_004_BEST_ACCURACY_BRANCH_PRESERVED_"
        "NO_FURTHER_HYPERPARAMETER_TUNING_UNDER_INCOMPATIBLE_RESIDUAL_"
        "CONSERVATIVE_MOVING_FAN_COORDINATE_RESIDUAL_DERIVATION_REQUIRED_BEFORE_NEW_TRAINING_"
        "NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
        if ok else
        "V16E1B2M_XPU_RECONCILIATION_FREEZE_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            "V16E-1B2M-XPU",

        "status":
            status,

        "interpretation_sha256":
            sha256(INTERPRETATION),

        "branch_roles_sha256":
            sha256(BRANCHES),

        "handoff_sha256":
            sha256(HANDOFF),

        "source_faithful_lineage_preserved":
            bool(ok),

        "best_accuracy_branch":
            "V16E-BLREP-COMP-XPU-004" if ok else None,

        "best_accuracy_checkpoint_sha256":
            COMP004_CHECKPOINT_SHA if ok else None,

        "new_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2N — derive conservative Stage-2 PDE residual in the "
                "moving fan coordinate xi=xD/xD_star(tD), including the required "
                "chain rule and xD_star time dependence, before implementation"
                if ok else
                "V16E-1B2M-R1 — diagnose failed reconciliation gate"
            ),

        "gates":
            {
                k: bool(v)
                for k, v
                in gates.items()
            },
    }

    SUMMARY.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Interpretation:", sha256(INTERPRETATION))
    print("  Branch roles  :", sha256(BRANCHES))
    print("  Handoff       :", sha256(HANDOFF))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
