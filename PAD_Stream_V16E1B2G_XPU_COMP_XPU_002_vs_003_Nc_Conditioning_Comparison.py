#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2G-XPU
COMP-XPU-002 vs COMP-XPU-003 Scientific Comparison

Purpose
-------
Compare the frozen 800-epoch raw-Nc conditioner reproduction
(V16E-BLREP-COMP-XPU-002) against the frozen 800-epoch scaled-Nc conditioner
reproduction (V16E-BLREP-COMP-XPU-003).

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Comparison structure is inherited from frozen B2D:
  * overall reproduction-development diagnostic metrics,
  * per-Nc holdout MAE/RMSE/max error,
  * full-domain fine-grid Godunov error,
  * front-excluded fine-grid Godunov error,
  * front-position error,
  * Nc=0.30 / Nc=0 response ratios.

No numerical pass/fail threshold is invented.
B3 is NOT automatically authorized by this comparison.
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
MILESTONE = "V16E-1B2G-XPU"

# =============================================================================
# Frozen authorities
# =============================================================================

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# Frozen B2D comparison structure / COMP-XPU-002 evidence
B2D_SOURCE = R / "PAD_Stream_V16E1B2D_XPU_COMP_XPU_001_vs_002_Scientific_Comparison.py"
B2D_SOURCE_SHA = "ece92813cd9ccd59afd0c8eb708cc6964863d22d425acc47e20b55082c2efe00"

B2D_DIR = (
    R / "output"
    / "V16_E1B2D_XPU_COMPRESSIBLE_400_vs_800_COMPARISON"
)
B2D_COMPARISON = B2D_DIR / "V16E1B2D_COMP_XPU_001_vs_002_Comparison.json"
B2D_SUMMARY = B2D_DIR / "PAD_Stream_V16E1B2D_XPU_Summary.json"

B2D_COMPARISON_SHA = "e956f5eb82b34b5af9a085674d8c0ae34da666d65b0c478d37fa71af2ce974fc"
B2D_SUMMARY_SHA = "90af2e6e06b49f220e9cbb61fa84ee21312e8d45311c97ff95bc5e75b4210f8c"

# COMP-XPU-002
COMP002_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-002"
)
COMP002_CHECKPOINT = COMP002_DIR / "V16E_BLREP_COMP_XPU_002.pt"
COMP002_METRICS = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Metrics.json"
COMP002_MANIFEST = COMP002_DIR / "V16E_BLREP_COMP_XPU_002_Manifest.json"
COMP002_SUMMARY = COMP002_DIR / "PAD_Stream_V16E1B2C_XPU_Summary.json"

COMP002_CHECKPOINT_SHA = "fca205b1981fbbdf15424af8ac8174df88ff7addf99e718548319a81f87d271b"
COMP002_METRICS_SHA = "f17fa9f5d6e5954119dc3e412fc01052b4cfb6173c157ac71ff1aa04b0a0385d"
COMP002_MANIFEST_SHA = "3ab6abb7fe60ef5e6dcacfa3f543c65578a39fb64b0219357a658604edc1a48f"
COMP002_SUMMARY_SHA = "8ede892568a1e21c989f5c2782a3f0696e00480a0d671771e6fead754a6b9788"

# COMP-XPU-003 / B2F
B2F_SOURCE = R / "PAD_Stream_V16E1B2F_XPU_COMP_XPU_003_Nc_Conditioning_Scale_Reproduction.py"
B2F_SOURCE_SHA = "6170abb221bca66ff6be30bb5c2f7c95637f38218affe2523e5376fe57171e53"

COMP003_DIR = (
    R / "output" / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-COMP-XPU-003"
)
COMP003_PORT = COMP003_DIR / "V16E_BLREP_COMP_XPU_003_Framework_Port_Protocol.json"
COMP003_CHECKPOINT = COMP003_DIR / "V16E_BLREP_COMP_XPU_003.pt"
COMP003_CONFIG = COMP003_DIR / "V16E_BLREP_COMP_XPU_003_Config.json"
COMP003_HISTORY = COMP003_DIR / "V16E_BLREP_COMP_XPU_003_Training_History.json"
COMP003_METRICS = COMP003_DIR / "V16E_BLREP_COMP_XPU_003_Metrics.json"
COMP003_MANIFEST = COMP003_DIR / "V16E_BLREP_COMP_XPU_003_Manifest.json"
COMP003_SUMMARY = COMP003_DIR / "PAD_Stream_V16E1B2F_XPU_Summary.json"

COMP003_PORT_SHA = "e681d1052178cfaf7fdc4da47e82442659dfb82b648d610741db831000bc1211"
COMP003_CHECKPOINT_SHA = "8657d2d65ad6612511d87b654b9a674523a68b716f706bc04be9f640d82a0797"
COMP003_CONFIG_SHA = "68127fb8b75d473a5edb805de373852b6530fa4f2db4df6f295f53b3459a8099"
COMP003_HISTORY_SHA = "8bbc0efe4f67b8d9e1c7b81d689d2fd39e1381ab0279f143678698a2b10dfc9f"
COMP003_METRICS_SHA = "2cc643c3cf1379f5d761b947a538aa0a00a96cbd650c638c6fbdab38428c409a"
COMP003_MANIFEST_SHA = "6fd9fbd71a04930b55f7efc779f843d83f36b701bb7c73ac6ee08be3a0844562"
COMP003_SUMMARY_SHA = "0aebe2e0ca9a7c73f2657eedcb88e16534cb5d48352a6820451554601dbc814b"

EXPECTED_B2F_STATUS = (
    "V16E1B2F_XPU_COMP_XPU_003_NC_CONDITIONING_SCALE_REPRODUCTION_COMPLETE_"
    "PHYSICAL_NC_TEACHER_RESIDUAL_TRANSFORM_AND_DATASET_UNCHANGED_"
    "MODEL_CONDITIONER_NC_SCALED_0P30_TO_UNIT_INTERVAL_ONLY_"
    "FRESH_800_EPOCH_INTEL_XPU_TRAINING_COMPLETE_CHECKPOINT_AND_METRICS_SHA_BOUND_"
    "DIAGNOSTICS_FINITE_SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
    "V16E1B2G_COMP_XPU_002_VS_003_COMPARISON_REQUIRED_B3_NOT_YET_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2G_XPU_COMPRESSIBLE_COMP002_vs_COMP003_COMPARISON"
)
OUT.mkdir(parents=True, exist_ok=True)

COMPARISON = OUT / "V16E1B2G_COMP_XPU_002_vs_003_Comparison.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2G_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337


# =============================================================================
# Helpers
# =============================================================================

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


def pct_improvement(old, new):
    old = float(old)
    new = float(new)
    if old == 0.0:
        return None
    return float((old - new) / old * 100.0)


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def aggregate_errors(err):
    e = np.abs(np.asarray(err).ravel())
    return {
        "mae": float(np.mean(e)),
        "rmse": float(np.sqrt(np.mean(e**2))),
        "max_abs_error": float(np.max(e)),
        "p95_abs_error": float(np.quantile(e, 0.95)),
        "p99_abs_error": float(np.quantile(e, 0.99)),
        "n": int(e.size),
    }


def per_nc_holdout(model, arrays, holdout_idx, device):
    xi, Sw, p11, tD, ai, at = arrays
    out = {}

    for nc in NC_VALUES:
        mask = np.isclose(
            p11[holdout_idx, 10],
            nc,
            atol=1e-7,
        )
        ids = holdout_idx[mask]

        if len(ids) == 0:
            raise RuntimeError(f"No holdout profiles for Nc={nc}")

        pred_parts = []
        batch = 1024

        for i0 in range(0, len(ids), batch):
            sub = ids[i0:i0 + batch]

            with torch.no_grad():
                x = torch.from_numpy(
                    xi[sub]
                ).to(device)
                p_phys = torch.from_numpy(
                    p11[sub]
                ).to(device)
                pred = model(
                    x,
                    p_phys,
                ).cpu().numpy()

            pred_parts.append(pred)

        pred = np.concatenate(
            pred_parts,
            axis=0,
        )
        err = pred - Sw[ids]

        out[f"{nc:.2f}"] = {
            "profile_count": int(len(ids)),
            **aggregate_errors(err),
        }

    return out


def source_case_diagnostic(model, M, p_case, nc, device):
    """
    Same B2A/B2D diagnostic convention:
      full-domain error,
      front-excluded error,
      front-position error.
    """
    t_bt = M.breakthrough_time_days(
        p_case,
        Nc=nc,
    )
    times = np.linspace(
        100.0,
        0.95 * t_bt,
        8,
    )

    full_errors = []
    excluded_errors = []
    front_errors = []

    half_width = 5.0 / M.NX_REF * 3.0

    for t in times:
        r = M.predict_against_ref(
            model,
            p_case,
            float(t),
            nc,
            device,
        )

        pred = np.interp(
            r["xD_true"],
            r["xD_pred"],
            r["Sw_pred"],
        )
        err = pred - r["Sw_true"]

        full_errors.append(err)

        mask = (
            np.abs(
                r["xD_true"]
                - r["xD_star_true"]
            )
            > half_width
        )
        excluded_errors.append(
            err[mask]
        )

        grid = np.linspace(
            p_case["swc"],
            1.0 - p_case["sor"],
            800,
        )
        _, fw = M.dfw_dsw_np(
            grid,
            p_case,
        )
        Sw_star, _, _, _ = M.welge_tangent(
            grid,
            fw,
            p_case["swc"],
        )

        pred_front = M.godunov_front_from_profile(
            r["xD_pred"],
            r["Sw_pred"],
            Sw_star,
            p_case["swc"],
        )

        if (
            np.isfinite(pred_front)
            and np.isfinite(r["xD_star_true"])
        ):
            front_errors.append(
                float(
                    pred_front
                    - r["xD_star_true"]
                )
            )

    fe = np.asarray(
        front_errors,
        dtype=float,
    )

    return {
        "Nc": float(nc),
        "front_exclusion_half_width_xD":
            float(half_width),
        "full_domain":
            aggregate_errors(
                np.concatenate(full_errors)
            ),
        "front_excluded":
            aggregate_errors(
                np.concatenate(excluded_errors)
            ),
        "front_position": {
            "mean_signed_error_xD":
                float(np.mean(fe)),
            "mae_xD":
                float(np.mean(np.abs(fe))),
            "max_abs_error_xD":
                float(np.max(np.abs(fe))),
            "n":
                int(len(fe)),
        },
    }


def ratio_030_over_000(records, metric):
    return float(
        records["0.30"][metric]
        / max(
            float(records["0.00"][metric]),
            1e-30,
        )
    )


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2G-XPU")
    print("COMP-XPU-002 vs COMP-XPU-003 Scientific Comparison")
    print("=" * 80)
    print("NO TRAINING — comparison only.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "B2G summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "B2D_source_SHA_exact":
            exact(B2D_SOURCE, B2D_SOURCE_SHA),
        "B2D_comparison_SHA_exact":
            exact(B2D_COMPARISON, B2D_COMPARISON_SHA),
        "B2D_summary_SHA_exact":
            exact(B2D_SUMMARY, B2D_SUMMARY_SHA),

        "COMP002_checkpoint_SHA_exact":
            exact(
                COMP002_CHECKPOINT,
                COMP002_CHECKPOINT_SHA,
            ),
        "COMP002_metrics_SHA_exact":
            exact(
                COMP002_METRICS,
                COMP002_METRICS_SHA,
            ),
        "COMP002_manifest_SHA_exact":
            exact(
                COMP002_MANIFEST,
                COMP002_MANIFEST_SHA,
            ),
        "COMP002_summary_SHA_exact":
            exact(
                COMP002_SUMMARY,
                COMP002_SUMMARY_SHA,
            ),

        "B2F_source_SHA_exact":
            exact(B2F_SOURCE, B2F_SOURCE_SHA),
        "COMP003_port_SHA_exact":
            exact(COMP003_PORT, COMP003_PORT_SHA),
        "COMP003_checkpoint_SHA_exact":
            exact(
                COMP003_CHECKPOINT,
                COMP003_CHECKPOINT_SHA,
            ),
        "COMP003_config_SHA_exact":
            exact(
                COMP003_CONFIG,
                COMP003_CONFIG_SHA,
            ),
        "COMP003_history_SHA_exact":
            exact(
                COMP003_HISTORY,
                COMP003_HISTORY_SHA,
            ),
        "COMP003_metrics_SHA_exact":
            exact(
                COMP003_METRICS,
                COMP003_METRICS_SHA,
            ),
        "COMP003_manifest_SHA_exact":
            exact(
                COMP003_MANIFEST,
                COMP003_MANIFEST_SHA,
            ),
        "COMP003_summary_SHA_exact":
            exact(
                COMP003_SUMMARY,
                COMP003_SUMMARY_SHA,
            ),
    }

    b2f_summary = read_json(
        COMP003_SUMMARY
    ) if COMP003_SUMMARY.exists() else {}

    gates.update({
        "B2F_status_exact":
            b2f_summary.get("status")
            == EXPECTED_B2F_STATUS,
        "B2F_B3_false":
            b2f_summary.get(
                "B3_authorized"
            )
            is False,
        "B2F_comparison_required":
            b2f_summary.get(
                "comparison_required_before_B3"
            )
            is True,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(gates.values()):
        raise RuntimeError(
            "B2G blocked by artifact authority mismatch."
        )

    # Import exact B2F implementation and its frozen base physics runner.
    F = import_module(
        B2F_SOURCE,
        "v16e1b2f_comp003",
    )
    M = F.import_base_runner()
    ScaledModel = F.build_scaled_model_class(M)

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2G evaluation."
        )

    device = torch.device("xpu")

    payload = torch.load(
        COMP003_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    model = ScaledModel()
    model.load_state_dict(
        payload["model_state_dict"],
        strict=True,
    )
    model.to(device)
    model.eval()

    gates.update({
        "COMP003_model_eval_mode":
            model.training is False,
        "COMP003_checkpoint_unchanged":
            sha256(COMP003_CHECKPOINT)
            == COMP003_CHECKPOINT_SHA,
        "COMP003_physical_Nc_unchanged_flag":
            payload.get(
                "physical_Nc_unchanged"
            )
            is True,
        "COMP003_scale_denominator_exact":
            float(
                payload.get(
                    "conditioner_Nc_scale_denominator"
                )
            )
            == 0.30,
    })

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

    rng = np.random.default_rng(SEED)
    idx = np.arange(len(xi))
    rng.shuffle(idx)
    n_train = int(0.8 * len(idx))
    holdout_idx = idx[n_train:]

    # -----------------------------------------------------------------
    # Recompute COMP-XPU-003 B2D-style diagnostics.
    # -----------------------------------------------------------------

    print("\nCOMP-XPU-003 PER-Nc HOLDOUT")
    new_holdout = per_nc_holdout(
        model,
        arrays,
        holdout_idx,
        device,
    )

    for nc, vals in new_holdout.items():
        print(
            f"  Nc={nc} "
            f"| MAE={vals['mae']:.6e} "
            f"| RMSE={vals['rmse']:.6e} "
            f"| max={vals['max_abs_error']:.6e}"
        )

    p1 = M.make_case(
        no=2.0,
        nw=2.0,
        swc=0.20,
        sor=0.20,
        mu_w=0.5,
        mu_o=0.7,
        phi=0.20,
    )

    p2 = M.make_case(
        no=3.0,
        nw=2.0,
        swc=0.15,
        sor=0.25,
        mu_w=6.0,
        mu_o=0.9,
        phi=0.25,
    )

    new_cases = {
        "case1": {},
        "case2": {},
    }

    print("\nCOMP-XPU-003 FULL vs FRONT-EXCLUDED")
    for label, p_case in (
        ("case1", p1),
        ("case2", p2),
    ):
        for nc in NC_VALUES:
            rec = source_case_diagnostic(
                model,
                M,
                p_case,
                nc,
                device,
            )
            new_cases[label][
                f"{nc:.2f}"
            ] = rec

            print(
                f"  {label} Nc={nc:.2f} "
                f"| full={rec['full_domain']['mae']:.6e} "
                f"| excl={rec['front_excluded']['mae']:.6e} "
                f"| front={rec['front_position']['mae_xD']:.6e}"
            )

    # -----------------------------------------------------------------
    # Frozen COMP-XPU-002 evidence from B2D.
    # -----------------------------------------------------------------

    b2d_comp = read_json(
        B2D_COMPARISON
    )
    old_metrics = read_json(
        COMP002_METRICS
    )
    new_metrics = read_json(
        COMP003_METRICS
    )

    old_overall = old_metrics["holdout"]
    new_overall = new_metrics["holdout"]

    # B2D stores 001 vs 002; pull exact COMP-XPU-002 side.
    old_holdout = {}
    for nc, rec in b2d_comp[
        "per_Nc_holdout_comparison"
    ].items():
        old_holdout[nc] = {
            metric:
                float(values["COMP_XPU_002"])
            for metric, values in rec.items()
        }

    old_cases = {
        "case1": {},
        "case2": {},
    }

    for label in ("case1", "case2"):
        for nc, rec in b2d_comp[
            "case_comparison"
        ][label].items():
            old_cases[label][nc] = {
                "full_domain": {
                    "mae":
                        float(
                            rec[
                                "full_domain_mae"
                            ]["COMP_XPU_002"]
                        )
                },
                "front_excluded": {
                    "mae":
                        float(
                            rec[
                                "front_excluded_mae"
                            ]["COMP_XPU_002"]
                        )
                },
                "front_position": {
                    "mae_xD":
                        float(
                            rec[
                                "front_position_mae_xD"
                            ]["COMP_XPU_002"]
                        )
                },
            }

    # -----------------------------------------------------------------
    # Direct comparisons.
    # -----------------------------------------------------------------

    overall_compare = {}

    for metric in (
        "mse",
        "rmse",
        "mae",
        "max_abs_error",
    ):
        old = float(
            old_overall[metric]
        )
        new = float(
            new_overall[metric]
        )

        overall_compare[metric] = {
            "COMP_XPU_002": old,
            "COMP_XPU_003": new,
            "percent_improvement_positive_is_better":
                pct_improvement(
                    old,
                    new,
                ),
        }

    per_nc_compare = {}

    for nc in [
        f"{x:.2f}"
        for x in NC_VALUES
    ]:
        per_nc_compare[nc] = {}

        for metric in (
            "mae",
            "rmse",
            "max_abs_error",
        ):
            old = float(
                old_holdout[nc][metric]
            )
            new = float(
                new_holdout[nc][metric]
            )

            per_nc_compare[nc][metric] = {
                "COMP_XPU_002": old,
                "COMP_XPU_003": new,
                "percent_improvement_positive_is_better":
                    pct_improvement(
                        old,
                        new,
                    ),
            }

    case_compare = {
        "case1": {},
        "case2": {},
    }

    for label in (
        "case1",
        "case2",
    ):
        for nc in [
            f"{x:.2f}"
            for x in NC_VALUES
        ]:
            case_compare[label][nc] = {}

            for output_key, old_branch, new_branch in (
                (
                    "full_domain_mae",
                    old_cases[label][nc]["full_domain"],
                    new_cases[label][nc]["full_domain"],
                ),
                (
                    "front_excluded_mae",
                    old_cases[label][nc]["front_excluded"],
                    new_cases[label][nc]["front_excluded"],
                ),
                (
                    "front_position_mae_xD",
                    old_cases[label][nc]["front_position"],
                    new_cases[label][nc]["front_position"],
                ),
            ):
                metric = (
                    "mae_xD"
                    if output_key
                    == "front_position_mae_xD"
                    else "mae"
                )

                old = float(
                    old_branch[metric]
                )
                new = float(
                    new_branch[metric]
                )

                case_compare[label][nc][output_key] = {
                    "COMP_XPU_002": old,
                    "COMP_XPU_003": new,
                    "percent_improvement_positive_is_better":
                        pct_improvement(
                            old,
                            new,
                        ),
                }

    # Response ratios.
    old_holdout_ratio = ratio_030_over_000(
        old_holdout,
        "mae",
    )
    new_holdout_ratio = ratio_030_over_000(
        new_holdout,
        "mae",
    )

    old_case1_full_records = {
        nc: {
            "mae":
                old_cases[
                    "case1"
                ][nc][
                    "full_domain"
                ]["mae"]
        }
        for nc in old_cases["case1"]
    }

    new_case1_full_records = {
        nc: {
            "mae":
                new_cases[
                    "case1"
                ][nc][
                    "full_domain"
                ]["mae"]
        }
        for nc in new_cases["case1"]
    }

    old_case1_excl_records = {
        nc: {
            "mae":
                old_cases[
                    "case1"
                ][nc][
                    "front_excluded"
                ]["mae"]
        }
        for nc in old_cases["case1"]
    }

    new_case1_excl_records = {
        nc: {
            "mae":
                new_cases[
                    "case1"
                ][nc][
                    "front_excluded"
                ]["mae"]
        }
        for nc in new_cases["case1"]
    }

    old_case1_full_ratio = ratio_030_over_000(
        old_case1_full_records,
        "mae",
    )
    new_case1_full_ratio = ratio_030_over_000(
        new_case1_full_records,
        "mae",
    )

    old_case1_excl_ratio = ratio_030_over_000(
        old_case1_excl_records,
        "mae",
    )
    new_case1_excl_ratio = ratio_030_over_000(
        new_case1_excl_records,
        "mae",
    )

    ratios = {
        "holdout_Nc030_over_Nc000": {
            "COMP_XPU_002":
                old_holdout_ratio,
            "COMP_XPU_003":
                new_holdout_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(
                    old_holdout_ratio,
                    new_holdout_ratio,
                ),
        },

        "case1_full_domain_Nc030_over_Nc000": {
            "COMP_XPU_002":
                old_case1_full_ratio,
            "COMP_XPU_003":
                new_case1_full_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(
                    old_case1_full_ratio,
                    new_case1_full_ratio,
                ),
        },

        "case1_front_excluded_Nc030_over_Nc000": {
            "COMP_XPU_002":
                old_case1_excl_ratio,
            "COMP_XPU_003":
                new_case1_excl_ratio,
            "percent_ratio_reduction_positive_is_flatter":
                pct_improvement(
                    old_case1_excl_ratio,
                    new_case1_excl_ratio,
                ),
        },
    }

    comparison = {
        "milestone": MILESTONE,
        "classification":
            "NO_TRAINING_COMP002_VS_COMP003_NC_CONDITIONING_SCALE_COMPARISON",

        "experiment_1": {
            "id":
                "V16E-BLREP-COMP-XPU-002",
            "epochs":
                800,
            "conditioner_Nc":
                "raw physical Nc",
            "checkpoint_sha256":
                COMP002_CHECKPOINT_SHA,
        },

        "experiment_2": {
            "id":
                "V16E-BLREP-COMP-XPU-003",
            "epochs":
                800,
            "conditioner_Nc":
                "physical Nc / 0.30",
            "physical_Nc_changed":
                False,
            "checkpoint_sha256":
                COMP003_CHECKPOINT_SHA,
        },

        "overall_comparison":
            overall_compare,
        "per_Nc_holdout_comparison":
            per_nc_compare,
        "case_comparison":
            case_compare,
        "Nc_response_ratios":
            ratios,

        "interpretation_policy":
            "No numeric pass/fail threshold is introduced. Determine whether "
            "Nc conditioner scaling improves absolute error and whether it "
            "meaningfully flattens the relative high-Nc response in the general "
            "holdout and front-excluded diagnostics.",

        "B3_automatically_authorized":
            False,
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
    }

    COMPARISON.write_text(
        json.dumps(
            comparison,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "COMP003_per_Nc_metrics_finite":
            all(
                finite(v[m])
                for v in new_holdout.values()
                for m in (
                    "mae",
                    "rmse",
                    "max_abs_error",
                )
            ),

        "COMP003_case_metrics_finite":
            all(
                finite(
                    rec[
                        "full_domain"
                    ]["mae"]
                )
                and finite(
                    rec[
                        "front_excluded"
                    ]["mae"]
                )
                and finite(
                    rec[
                        "front_position"
                    ]["mae_xD"]
                )
                for case
                in new_cases.values()
                for rec
                in case.values()
            ),

        "comparison_written":
            COMPARISON.exists()
            and COMPARISON.stat().st_size > 0,

        "COMP003_checkpoint_still_unchanged":
            sha256(COMP003_CHECKPOINT)
            == COMP003_CHECKPOINT_SHA,

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

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2G_XPU_COMP_XPU_002_VS_003_NC_CONDITIONING_SCALE_COMPARISON_COMPLETE_"
        "OVERALL_PER_NC_HOLDOUT_FULL_DOMAIN_FRONT_EXCLUDED_FRONT_POSITION_AND_RESPONSE_RATIOS_FROZEN_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "B3_DECISION_REQUIRES_INTERPRETATION"
        if ok else
        "V16E1B2G_XPU_COMPARISON_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,
        "status":
            status,
        "comparison_sha256":
            sha256(COMPARISON),

        "B3_authorized":
            False,
        "B3_decision_requires_interpretation":
            True,

        "overall_RMSE_percent_improvement":
            overall_compare[
                "rmse"
            ][
                "percent_improvement_positive_is_better"
            ],

        "overall_MAE_percent_improvement":
            overall_compare[
                "mae"
            ][
                "percent_improvement_positive_is_better"
            ],

        "holdout_ratio_COMP002":
            old_holdout_ratio,
        "holdout_ratio_COMP003":
            new_holdout_ratio,

        "case1_full_ratio_COMP002":
            old_case1_full_ratio,
        "case1_full_ratio_COMP003":
            new_case1_full_ratio,

        "case1_front_excluded_ratio_COMP002":
            old_case1_excl_ratio,
        "case1_front_excluded_ratio_COMP003":
            new_case1_excl_ratio,

        "gates": {
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

    print("\nCOMP-XPU-002 vs COMP-XPU-003 SUMMARY")
    print(
        "  Overall RMSE improvement:",
        f"{summary['overall_RMSE_percent_improvement']:.3f}%"
    )
    print(
        "  Overall MAE improvement :",
        f"{summary['overall_MAE_percent_improvement']:.3f}%"
    )
    print(
        "  Holdout Nc0.30/Nc0 ratio:",
        f"{old_holdout_ratio:.4f}x -> {new_holdout_ratio:.4f}x"
    )
    print(
        "  Case1 full ratio        :",
        f"{old_case1_full_ratio:.4f}x -> {new_case1_full_ratio:.4f}x"
    )
    print(
        "  Case1 front-excl ratio  :",
        f"{old_case1_excl_ratio:.4f}x -> {new_case1_excl_ratio:.4f}x"
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(" ", status)

    print("\nHASHES")
    print(
        "  Comparison:",
        sha256(COMPARISON),
    )
    print(
        "  Summary   :",
        sha256(SUMMARY),
    )

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
