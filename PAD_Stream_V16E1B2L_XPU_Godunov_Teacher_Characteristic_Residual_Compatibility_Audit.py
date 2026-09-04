#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2L-XPU
Godunov Teacher vs Characteristic Physics-Residual Compatibility Audit

Purpose
-------
Resolve the remaining Stage-2 question exposed by B2K:

COMP-XPU-004 improves:
  * global RMSE/MAE,
  * every per-Nc holdout MAE,
  * most source-case errors,
  * most model-to-teacher Nc response gains,

but:
  * the general Nc=0.30/Nc=0 holdout ratio remains elevated,
  * high-Nc physics loss is larger than COMP-XPU-002 for Nc >= 0.10,
  * the final Case-2 0.20->0.30 response gain worsens.

The frozen Stage-2 Godunov variant explicitly trains on conservative finite-
volume truth while retaining the characteristic residual:

    R = y(xi*xD_star;Nc) - tD * dfw/dS

This audit evaluates THAT EXACT frozen physics loss directly on the frozen
Godunov teacher saturation profiles.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Questions
---------
1. How large is the characteristic residual on the Godunov truth itself?
2. Does teacher residual MSE rise systematically with physical Nc?
3. How do COMP-XPU-002 and COMP-XPU-004 physics losses compare with the
   teacher's own residual floor?
4. Is the apparent high-Nc "physics-loss degradation" a model problem, a
   teacher/residual compatibility issue, or a mixture?

No numerical pass/fail threshold is invented.
B3 remains blocked pending interpretation.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

import numpy as np
import torch


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2L-XPU"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# B2K authority
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

OUT = (
    R / "output"
    / "V16_E1B2L_XPU_GODUNOV_TEACHER_CHARACTERISTIC_RESIDUAL_AUDIT"
)
OUT.mkdir(parents=True, exist_ok=True)

AUDIT = OUT / "V16E1B2L_Godunov_Teacher_Characteristic_Residual_Audit.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2L_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337
BATCH = 256


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


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def split_indices(n):
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(0.8 * n)
    return idx[:n_train], idx[n_train:]


def teacher_physics_loss_for_ids(M, arrays, ids, device):
    """
    Evaluate the EXACT frozen Stage-2 physics_loss_char with S_pred replaced by
    the frozen Godunov target Sw. This measures teacher/residual compatibility.

    physics_loss_char needs autograd through S to obtain dfw/dS, so S_true is
    cloned as a leaf with requires_grad=True. No model or optimizer is used.
    """
    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    weighted = 0.0
    count = 0

    for i0 in range(0, len(ids), BATCH):
        sub = ids[i0:i0 + BATCH]
        n = len(sub)

        xi = torch.from_numpy(xi_all[sub]).to(device)
        p11 = torch.from_numpy(p11_all[sub]).to(device)
        tD = torch.from_numpy(tD_all[sub]).to(device)

        S_teacher = (
            torch.from_numpy(Sw_all[sub])
            .to(device)
            .detach()
            .clone()
            .requires_grad_(True)
        )

        with torch.enable_grad():
            Lp = M.physics_loss_char(
                xi,
                S_teacher,
                tD,
                p11,
            )

        value = float(Lp.detach().cpu())
        weighted += value * n
        count += n

        del xi, p11, tD, S_teacher, Lp

    M.sync_xpu()

    return float(weighted / max(count, 1))


def per_nc_teacher_losses(M, arrays, indices, device):
    p11 = arrays[2]
    out = {}

    for nc in NC_VALUES:
        key = f"{nc:.2f}"
        ids = indices[
            np.isclose(
                p11[indices, 10],
                nc,
                atol=1e-7,
            )
        ]

        if len(ids) == 0:
            raise RuntimeError(f"No profiles for Nc={nc}")

        out[key] = {
            "profiles": int(len(ids)),
            "teacher_characteristic_physics_mse":
                teacher_physics_loss_for_ids(
                    M,
                    arrays,
                    ids,
                    device,
                ),
        }

    return out


def ratio_030_over_000(records, field):
    return float(
        records["0.30"][field]
        / max(
            float(records["0.00"][field]),
            1e-30,
        )
    )


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2L-XPU")
    print("Godunov Teacher vs Characteristic Physics-Residual Compatibility Audit")
    print("=" * 80)
    print("NO TRAINING — teacher/residual compatibility audit only.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "B2L summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),
        "B2K_source_SHA_exact":
            exact(B2K_SOURCE, B2K_SOURCE_SHA),
        "B2K_comparison_SHA_exact":
            exact(B2K_COMPARISON, B2K_COMPARISON_SHA),
        "B2K_summary_SHA_exact":
            exact(B2K_SUMMARY, B2K_SUMMARY_SHA),
    }

    b2k_summary = read_json(B2K_SUMMARY) if B2K_SUMMARY.exists() else {}

    gates.update({
        "B2K_status_exact":
            b2k_summary.get("status") == EXPECTED_B2K_STATUS,
        "B2K_B3_false":
            b2k_summary.get("B3_authorized") is False,
        "B2K_interpretation_required":
            b2k_summary.get("B3_decision_requires_interpretation") is True,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2L blocked by artifact authority mismatch."
        )

    M = import_module(
        BASE_RUNNER,
        "v16e1b2c_base",
    )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2L physics audit."
        )

    device = torch.device("xpu")

    d = np.load(DATASET)
    arrays = (
        d["xi"],
        d["Sw"],
        d["p11"],
        d["tD"],
        d["ai"],
        d["at"],
    )

    xi, Sw, p11, tD, ai, at = arrays
    train_idx, holdout_idx = split_indices(len(xi))

    gates.update({
        "dataset_xi_shape_exact":
            tuple(xi.shape) == (14400, 64, 1),
        "dataset_p11_shape_exact":
            tuple(p11.shape) == (14400, 11),
        "physical_Nc_min_0":
            np.isclose(float(np.min(p11[:, 10])), 0.0, atol=1e-7),
        "physical_Nc_max_0p30":
            np.isclose(float(np.max(p11[:, 10])), 0.30, atol=1e-7),
    })

    print("\nGODUNOV TEACHER CHARACTERISTIC PHYSICS LOSS — TRAIN")
    teacher_train = per_nc_teacher_losses(
        M,
        arrays,
        train_idx,
        device,
    )

    for nc, rec in teacher_train.items():
        print(
            f"  Nc={nc} | profiles={rec['profiles']} "
            f"| teacher_phys={rec['teacher_characteristic_physics_mse']:.6e}"
        )

    print("\nGODUNOV TEACHER CHARACTERISTIC PHYSICS LOSS — HOLDOUT")
    teacher_holdout = per_nc_teacher_losses(
        M,
        arrays,
        holdout_idx,
        device,
    )

    for nc, rec in teacher_holdout.items():
        print(
            f"  Nc={nc} | profiles={rec['profiles']} "
            f"| teacher_phys={rec['teacher_characteristic_physics_mse']:.6e}"
        )

    # Read exact model physics losses already frozen by B2K.
    b2k = read_json(B2K_COMPARISON)
    loss_comp = b2k["per_Nc_loss_comparison"]

    model_phys = {
        "COMP_XPU_002": {},
        "COMP_XPU_004": {},
    }

    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        model_phys["COMP_XPU_002"][nc] = float(
            loss_comp[nc]["physics"]["COMP_XPU_002"]
        )
        model_phys["COMP_XPU_004"][nc] = float(
            loss_comp[nc]["physics"]["COMP_XPU_004"]
        )

    compatibility = {}

    print("\nMODEL PHYSICS LOSS RELATIVE TO GODUNOV TEACHER RESIDUAL — HOLDOUT")
    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        teacher = float(
            teacher_holdout[nc]["teacher_characteristic_physics_mse"]
        )
        p2 = model_phys["COMP_XPU_002"][nc]
        p4 = model_phys["COMP_XPU_004"][nc]

        compatibility[nc] = {
            "teacher_characteristic_physics_mse":
                teacher,

            "COMP_XPU_002_physics_mse":
                p2,

            "COMP_XPU_004_physics_mse":
                p4,

            "COMP_XPU_002_minus_teacher":
                float(p2 - teacher),

            "COMP_XPU_004_minus_teacher":
                float(p4 - teacher),

            "COMP_XPU_002_over_teacher":
                float(p2 / max(teacher, 1e-30)),

            "COMP_XPU_004_over_teacher":
                float(p4 / max(teacher, 1e-30)),
        }

        print(
            f"  Nc={nc} "
            f"| teacher={teacher:.6e} "
            f"| COMP002={p2:.6e} "
            f"| COMP004={p4:.6e} "
            f"| 002-teacher={p2-teacher:+.6e} "
            f"| 004-teacher={p4-teacher:+.6e}"
        )

    teacher_train_ratio = ratio_030_over_000(
        teacher_train,
        "teacher_characteristic_physics_mse",
    )
    teacher_holdout_ratio = ratio_030_over_000(
        teacher_holdout,
        "teacher_characteristic_physics_mse",
    )

    model002_ratio = float(
        model_phys["COMP_XPU_002"]["0.30"]
        / max(model_phys["COMP_XPU_002"]["0.00"], 1e-30)
    )
    model004_ratio = float(
        model_phys["COMP_XPU_004"]["0.30"]
        / max(model_phys["COMP_XPU_004"]["0.00"], 1e-30)
    )

    print("\nNc=0.30 / Nc=0 PHYSICS-LOSS RATIOS")
    print(
        f"  Godunov teacher train  : {teacher_train_ratio:.4f}x"
    )
    print(
        f"  Godunov teacher holdout: {teacher_holdout_ratio:.4f}x"
    )
    print(
        f"  COMP-XPU-002 holdout   : {model002_ratio:.4f}x"
    )
    print(
        f"  COMP-XPU-004 holdout   : {model004_ratio:.4f}x"
    )

    audit = {
        "milestone":
            MILESTONE,

        "classification":
            "NO_TRAINING_GODUNOV_TEACHER_VS_CHARACTERISTIC_RESIDUAL_COMPATIBILITY_AUDIT",

        "physics_residual_definition":
            "R = y(xi*xD_star;Nc) - tD*dfw/dS; physics loss = mean(R^2) "
            "over interior fan sequence nodes",

        "teacher_truth":
            "exact frozen conservative Godunov Stage-2 dataset saturation profiles",

        "teacher_characteristic_physics_loss": {
            "train":
                teacher_train,
            "holdout":
                teacher_holdout,
        },

        "frozen_model_holdout_physics_loss": {
            "COMP_XPU_002":
                model_phys["COMP_XPU_002"],
            "COMP_XPU_004":
                model_phys["COMP_XPU_004"],
        },

        "model_vs_teacher_compatibility":
            compatibility,

        "Nc030_over_Nc000_physics_loss_ratios": {
            "Godunov_teacher_train":
                teacher_train_ratio,
            "Godunov_teacher_holdout":
                teacher_holdout_ratio,
            "COMP_XPU_002_holdout":
                model002_ratio,
            "COMP_XPU_004_holdout":
                model004_ratio,
        },

        "interpretation_policy":
            "No numerical threshold is introduced. If the frozen Godunov truth "
            "itself shows a strong Nc-dependent characteristic residual, then "
            "the retained characteristic physics loss is not a zero-residual "
            "constraint for the conservative teacher and the Stage-2 objectives "
            "must be interpreted as potentially competing. If teacher residual "
            "is negligible/flat while model residual rises, the remaining issue "
            "is model approximation/conditioning.",

        "B3_automatically_authorized":
            False,

        "training_executed":
            False,

        "optimizer_created":
            False,

        "weights_modified":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,
    }

    AUDIT.write_text(
        json.dumps(
            audit,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "teacher_train_losses_finite":
            all(
                finite(
                    rec["teacher_characteristic_physics_mse"]
                )
                for rec in teacher_train.values()
            ),

        "teacher_holdout_losses_finite":
            all(
                finite(
                    rec["teacher_characteristic_physics_mse"]
                )
                for rec in teacher_holdout.values()
            ),

        "compatibility_metrics_finite":
            all(
                finite(v)
                for rec in compatibility.values()
                for v in rec.values()
            ),

        "all_Nc_groups_present_train":
            set(teacher_train.keys())
            == {"0.00", "0.05", "0.10", "0.20", "0.30"},

        "all_Nc_groups_present_holdout":
            set(teacher_holdout.keys())
            == {"0.00", "0.05", "0.10", "0.20", "0.30"},

        "audit_written":
            AUDIT.exists()
            and AUDIT.stat().st_size > 0,

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

        "no_numeric_threshold":
            True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2L_XPU_GODUNOV_TEACHER_CHARACTERISTIC_RESIDUAL_COMPATIBILITY_AUDIT_COMPLETE_"
        "PER_NC_TRAIN_AND_HOLDOUT_TEACHER_PHYSICS_LOSSES_AND_MODEL_VS_TEACHER_RESIDUAL_GAPS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "STAGE2_CLOSURE_AND_B3_DECISION_REQUIRE_INTERPRETATION"
        if ok else
        "V16E1B2L_XPU_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "audit_sha256":
            sha256(AUDIT),

        "Godunov_teacher_train_Nc030_over_Nc000_physics_ratio":
            teacher_train_ratio,

        "Godunov_teacher_holdout_Nc030_over_Nc000_physics_ratio":
            teacher_holdout_ratio,

        "COMP_XPU_002_holdout_Nc030_over_Nc000_physics_ratio":
            model002_ratio,

        "COMP_XPU_004_holdout_Nc030_over_Nc000_physics_ratio":
            model004_ratio,

        "B3_authorized":
            False,

        "Stage2_closure_requires_interpretation":
            True,

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

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print("  Audit  :", sha256(AUDIT))
    print("  Summary:", sha256(SUMMARY))

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
