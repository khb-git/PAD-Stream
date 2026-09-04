#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2H-XPU
Compressible BL Nc Conditioning Response Audit

Purpose
-------
Diagnose WHY the relative high-Nc weakness persists after:
  * COMP-XPU-002: 800-epoch raw-Nc conditioner
  * COMP-XPU-003: 800-epoch Nc/0.30 model conditioner

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Questions
---------
1. Are the physical Nc groups materially imbalanced in the frozen train/holdout
   split?
2. How do reproduction data loss and physics loss vary by Nc for COMP002/003?
3. Does each model respond to physical Nc with the same profile-change magnitude
   as the conservative Godunov teacher?

This audit invents NO numerical acceptance threshold and authorizes NO new
training intervention by itself.
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
MILESTONE = "V16E-1B2H-XPU"

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# COMP-XPU-002
BASE_RUNNER = (
    R / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

COMP002_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)
COMP002_CHECKPOINT = COMP002_DIR / "V16E_BLREP_COMP_XPU_002.pt"
COMP002_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"

# COMP-XPU-003
B2F_SOURCE = (
    R / "PAD_Stream_V16E1B2F_XPU_COMP_XPU_003_Nc_Conditioning_Scale_Reproduction.py"
)
B2F_SOURCE_SHA = "6170abb221bca66ff6be30bb5c2f7c95637f38218affe2523e5376fe57171e53"

COMP003_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-003"
)
COMP003_CHECKPOINT = COMP003_DIR / "V16E_BLREP_COMP_XPU_003.pt"
COMP003_CHECKPOINT_SHA = "8657d2d65ad6612511d87b654b9a674523a68b716f706bc04be9f640d82a0797"

# B2G authority
B2G_SOURCE = (
    R / "PAD_Stream_V16E1B2G_XPU_COMP_XPU_002_vs_003_Nc_Conditioning_Comparison.py"
)
B2G_SOURCE_SHA = "18a8e63f0cc7de4c4e2093019c72b438f561bb2d66602c74b6e842bf13bd06aa"

B2G_DIR = (
    R / "output"
    / "V16_E1B2G_XPU_COMPRESSIBLE_COMP002_vs_COMP003_COMPARISON"
)
B2G_COMPARISON = B2G_DIR / "V16E1B2G_COMP_XPU_002_vs_003_Comparison.json"
B2G_SUMMARY = B2G_DIR / "PAD_Stream_V16E1B2G_XPU_Summary.json"

B2G_COMPARISON_SHA = "f283e87e1fb1ac115016846dd60817040e177714a2f2f117956554a530179320"
B2G_SUMMARY_SHA = "5d771ba5daba6e8630c5612aa8f1b76d0d9db73097486060e62fc663a29dee4b"

EXPECTED_B2G_STATUS = (
    "V16E1B2G_XPU_COMP_XPU_002_VS_003_NC_CONDITIONING_SCALE_COMPARISON_COMPLETE_"
    "OVERALL_PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_FRONT_POSITION_AND_RESPONSE_RATIOS_FROZEN_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "B3_DECISION_REQUIRES_INTERPRETATION"
)

OUT = R / "output" / "V16_E1B2H_XPU_NC_CONDITIONING_RESPONSE_AUDIT"
OUT.mkdir(parents=True, exist_ok=True)

AUDIT = OUT / "V16E1B2H_Nc_Conditioning_Response_Audit.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2H_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337


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


def load_models():
    M = import_module(BASE_RUNNER, "v16e1b2c_base")
    F = import_module(B2F_SOURCE, "v16e1b2f_scaled")
    ScaledModel = F.build_scaled_model_class(M)

    if not torch.xpu.is_available():
        raise RuntimeError("Intel XPU unavailable.")

    device = torch.device("xpu")

    p2 = torch.load(COMP002_CHECKPOINT, map_location="cpu", weights_only=False)
    m2 = M.CompressiblePIRNNXPU()
    m2.load_state_dict(p2["model_state_dict"], strict=True)
    m2.to(device)
    m2.eval()

    p3 = torch.load(COMP003_CHECKPOINT, map_location="cpu", weights_only=False)
    m3 = ScaledModel()
    m3.load_state_dict(p3["model_state_dict"], strict=True)
    m3.to(device)
    m3.eval()

    return M, m2, m3, device


def split_indices(n):
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(0.8 * n)
    return idx[:n_train], idx[n_train:]


def counts_by_nc(p11, indices):
    out = {}
    for nc in NC_VALUES:
        out[f"{nc:.2f}"] = int(
            np.sum(np.isclose(p11[indices, 10], nc, atol=1e-7))
        )
    return out


def eval_group_losses(M, model, arrays, ids, device, batch=512):
    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    sums = {
        "data": 0.0,
        "physics": 0.0,
        "bc_inj": 0.0,
        "bc_tip": 0.0,
        "anchor": 0.0,
        "mono": 0.0,
        "total": 0.0,
    }
    n_total = 0

    for i0 in range(0, len(ids), batch):
        sub = ids[i0:i0 + batch]
        n = len(sub)

        xi = torch.from_numpy(xi_all[sub]).to(device)
        Sw = torch.from_numpy(Sw_all[sub]).to(device)
        p11 = torch.from_numpy(p11_all[sub]).to(device)
        tD = torch.from_numpy(tD_all[sub]).to(device)
        ai = torch.from_numpy(ai_all[sub]).to(device)
        at = torch.from_numpy(at_all[sub]).to(device)

        with torch.enable_grad():
            _, parts = M.total_losses(
                model, xi, Sw, p11, tD, ai, at
            )

        for k in sums:
            sums[k] += float(parts[k].detach().cpu()) * n
        n_total += n

        del xi, Sw, p11, tD, ai, at, parts

    return {k: sums[k] / max(n_total, 1) for k in sums}


def per_nc_losses(M, model, arrays, indices, device):
    p11 = arrays[2]
    out = {}
    for nc in NC_VALUES:
        ids = indices[np.isclose(p11[indices, 10], nc, atol=1e-7)]
        out[f"{nc:.2f}"] = {
            "profiles": int(len(ids)),
            **eval_group_losses(M, model, arrays, ids, device),
        }
    return out


def full_profile_prediction(M, model, p_case, t_days, nc, device):
    r = M.predict_against_ref(model, p_case, float(t_days), nc, device)
    pred = np.interp(r["xD_true"], r["xD_pred"], r["Sw_pred"])
    return r["xD_true"], r["Sw_true"], pred, r["xD_star_true"]


def response_gain_for_case(M, model, p_case, device):
    """
    Compare model and teacher profile-change magnitude between adjacent Nc values
    at matched fractional times (100 d to 0.95*min breakthrough of pair).
    """
    out = {}

    for a, b in zip(NC_VALUES[:-1], NC_VALUES[1:]):
        tba = M.breakthrough_time_days(p_case, Nc=a)
        tbb = M.breakthrough_time_days(p_case, Nc=b)
        t_end = 0.95 * min(tba, tbb)

        if t_end <= 100.0:
            raise RuntimeError(
                f"Invalid matched-time range for Nc {a}->{b}: {t_end}"
            )

        times = np.linspace(100.0, t_end, 8)

        teacher_changes = []
        model_changes = []
        teacher_changes_excl = []
        model_changes_excl = []

        half_width = 5.0 / M.NX_REF * 3.0

        for t in times:
            xa, Sa_true, Sa_pred, fa = full_profile_prediction(
                M, model, p_case, t, a, device
            )
            xb, Sb_true, Sb_pred, fb = full_profile_prediction(
                M, model, p_case, t, b, device
            )

            # Both references use identical NX_REF grid.
            if not np.allclose(xa, xb):
                raise RuntimeError("Reference grids differ unexpectedly.")

            dtrue = Sb_true - Sa_true
            dpred = Sb_pred - Sa_pred

            teacher_changes.append(np.mean(np.abs(dtrue)))
            model_changes.append(np.mean(np.abs(dpred)))

            # Exclude thin front zones from BOTH adjacent states.
            mask = (
                (np.abs(xa - fa) > half_width)
                & (np.abs(xa - fb) > half_width)
            )
            teacher_changes_excl.append(np.mean(np.abs(dtrue[mask])))
            model_changes_excl.append(np.mean(np.abs(dpred[mask])))

        tchg = float(np.mean(teacher_changes))
        mchg = float(np.mean(model_changes))
        tchg_e = float(np.mean(teacher_changes_excl))
        mchg_e = float(np.mean(model_changes_excl))

        key = f"{a:.2f}->{b:.2f}"
        out[key] = {
            "Nc_a": float(a),
            "Nc_b": float(b),
            "delta_Nc": float(b - a),
            "teacher_mean_abs_profile_change": tchg,
            "model_mean_abs_profile_change": mchg,
            "model_to_teacher_response_gain":
                float(mchg / max(tchg, 1e-30)),
            "front_excluded_teacher_change": tchg_e,
            "front_excluded_model_change": mchg_e,
            "front_excluded_model_to_teacher_response_gain":
                float(mchg_e / max(tchg_e, 1e-30)),
        }

    return out


def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2H-XPU")
    print("Compressible BL Nc Conditioning Response Audit")
    print("=" * 80)
    print("NO TRAINING — diagnostic audit only.\n")

    if SUMMARY.exists():
        raise RuntimeError("B2H summary already exists; refusing overwrite.")

    gates = {
        "Stage2_SHA_exact": exact(STAGE2, STAGE2_SHA),
        "dataset_SHA_exact": exact(DATASET, DATASET_SHA),
        "base_runner_SHA_exact": exact(BASE_RUNNER, BASE_RUNNER_SHA),
        "COMP002_checkpoint_SHA_exact":
            exact(COMP002_CHECKPOINT, COMP002_CHECKPOINT_SHA),
        "B2F_source_SHA_exact": exact(B2F_SOURCE, B2F_SOURCE_SHA),
        "COMP003_checkpoint_SHA_exact":
            exact(COMP003_CHECKPOINT, COMP003_CHECKPOINT_SHA),
        "B2G_source_SHA_exact": exact(B2G_SOURCE, B2G_SOURCE_SHA),
        "B2G_comparison_SHA_exact":
            exact(B2G_COMPARISON, B2G_COMPARISON_SHA),
        "B2G_summary_SHA_exact":
            exact(B2G_SUMMARY, B2G_SUMMARY_SHA),
    }

    b2g = read_json(B2G_SUMMARY) if B2G_SUMMARY.exists() else {}
    gates.update({
        "B2G_status_exact":
            b2g.get("status") == EXPECTED_B2G_STATUS,
        "B2G_B3_false":
            b2g.get("B3_authorized") is False,
        "B2G_interpretation_required":
            b2g.get("B3_decision_requires_interpretation") is True,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError("B2H blocked by artifact authority mismatch.")

    M, model2, model3, device = load_models()

    d = np.load(DATASET)
    arrays = (
        d["xi"], d["Sw"], d["p11"],
        d["tD"], d["ai"], d["at"],
    )
    xi, Sw, p11, tD, ai, at = arrays

    train_idx, holdout_idx = split_indices(len(xi))

    counts = {
        "all": counts_by_nc(p11, np.arange(len(xi))),
        "train": counts_by_nc(p11, train_idx),
        "holdout": counts_by_nc(p11, holdout_idx),
    }

    print("\nPHYSICAL Nc PROFILE COUNTS")
    for split, rec in counts.items():
        print(" ", split)
        for nc, n in rec.items():
            print(f"    Nc={nc}: {n}")

    print("\nPER-Nc HOLDOUT LOSS COMPONENTS — COMP-XPU-002")
    losses2 = per_nc_losses(
        M, model2, arrays, holdout_idx, device
    )
    for nc, rec in losses2.items():
        print(
            f"  Nc={nc} | Data={rec['data']:.6e} "
            f"| Phys={rec['physics']:.6e} "
            f"| Total={rec['total']:.6e}"
        )

    print("\nPER-Nc HOLDOUT LOSS COMPONENTS — COMP-XPU-003")
    losses3 = per_nc_losses(
        M, model3, arrays, holdout_idx, device
    )
    for nc, rec in losses3.items():
        print(
            f"  Nc={nc} | Data={rec['data']:.6e} "
            f"| Phys={rec['physics']:.6e} "
            f"| Total={rec['total']:.6e}"
        )

    p1 = M.make_case(
        no=2.0, nw=2.0,
        swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7,
        phi=0.20,
    )
    p2 = M.make_case(
        no=3.0, nw=2.0,
        swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9,
        phi=0.25,
    )

    print("\nNc RESPONSE GAIN — CASE 1")
    gain2_c1 = response_gain_for_case(M, model2, p1, device)
    gain3_c1 = response_gain_for_case(M, model3, p1, device)

    for key in gain2_c1:
        print(
            f"  {key} | COMP002 gain={gain2_c1[key]['model_to_teacher_response_gain']:.4f} "
            f"| COMP003 gain={gain3_c1[key]['model_to_teacher_response_gain']:.4f} "
            f"| excl002={gain2_c1[key]['front_excluded_model_to_teacher_response_gain']:.4f} "
            f"| excl003={gain3_c1[key]['front_excluded_model_to_teacher_response_gain']:.4f}"
        )

    print("\nNc RESPONSE GAIN — CASE 2")
    gain2_c2 = response_gain_for_case(M, model2, p2, device)
    gain3_c2 = response_gain_for_case(M, model3, p2, device)

    for key in gain2_c2:
        print(
            f"  {key} | COMP002 gain={gain2_c2[key]['model_to_teacher_response_gain']:.4f} "
            f"| COMP003 gain={gain3_c2[key]['model_to_teacher_response_gain']:.4f} "
            f"| excl002={gain2_c2[key]['front_excluded_model_to_teacher_response_gain']:.4f} "
            f"| excl003={gain3_c2[key]['front_excluded_model_to_teacher_response_gain']:.4f}"
        )

    audit = {
        "milestone": MILESTONE,
        "classification": "NO_TRAINING_NC_CONDITIONING_RESPONSE_AUDIT",
        "source_statement":
            "Frozen Stage-2 source states rising Nc MAE means Nc conditioning "
            "is underweighted or undertrained, but does not prescribe a "
            "weighting mechanism.",
        "physical_Nc_counts": counts,
        "holdout_loss_components": {
            "COMP_XPU_002": losses2,
            "COMP_XPU_003": losses3,
        },
        "response_gain": {
            "case1": {
                "COMP_XPU_002": gain2_c1,
                "COMP_XPU_003": gain3_c1,
            },
            "case2": {
                "COMP_XPU_002": gain2_c2,
                "COMP_XPU_003": gain3_c2,
            },
        },
        "response_gain_definition":
            "mean absolute model profile change between adjacent physical Nc "
            "states divided by the corresponding Godunov teacher profile "
            "change, using matched times; 1.0 means equal change magnitude.",
        "decision_policy":
            "No new threshold. Use count balance, per-Nc data/physics loss "
            "behavior, and model-to-teacher response gains to choose the next "
            "prospective one-factor intervention.",
        "training_executed": False,
        "optimizer_created": False,
        "weights_modified": False,
        "OOD_used": False,
        "TOF_used": False,
        "B3_automatically_authorized": False,
    }

    AUDIT.write_text(
        json.dumps(audit, indent=2),
        encoding="utf-8",
    )

    gates.update({
        "counts_cover_all_Nc":
            all(str(f"{nc:.2f}") in counts["all"] for nc in NC_VALUES),
        "losses_finite":
            all(
                finite(rec[k])
                for model_rec in (losses2, losses3)
                for rec in model_rec.values()
                for k in ("data", "physics", "total")
            ),
        "response_gains_finite":
            all(
                finite(rec[k])
                for group in (gain2_c1, gain3_c1, gain2_c2, gain3_c2)
                for rec in group.values()
                for k in (
                    "model_to_teacher_response_gain",
                    "front_excluded_model_to_teacher_response_gain",
                )
            ),
        "COMP002_checkpoint_unchanged":
            sha256(COMP002_CHECKPOINT) == COMP002_CHECKPOINT_SHA,
        "COMP003_checkpoint_unchanged":
            sha256(COMP003_CHECKPOINT) == COMP003_CHECKPOINT_SHA,
        "audit_written":
            AUDIT.exists() and AUDIT.stat().st_size > 0,
        "no_training": True,
        "no_optimizer": True,
        "no_weight_update": True,
        "no_OOD": True,
        "no_TOF": True,
        "no_numeric_threshold": True,
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2H_XPU_NC_CONDITIONING_RESPONSE_AUDIT_COMPLETE_"
        "PHYSICAL_NC_COUNTS_PER_NC_LOSS_COMPONENTS_AND_MODEL_TO_TEACHER_RESPONSE_GAINS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "NEXT_INTERVENTION_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2H_XPU_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": MILESTONE,
        "status": status,
        "audit_sha256": sha256(AUDIT),
        "B3_authorized": False,
        "next_intervention_requires_interpretation": True,
        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(
        json.dumps(summary, indent=2),
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
