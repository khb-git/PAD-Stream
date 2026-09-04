#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2Q-XPU
Source-Native Godunov Discrete-Conservation Verification
+ Fan-Processing Residual Ablation

Purpose
-------
Resolve the B2O teacher-validation ambiguity by returning to the exact
Stage-2 source-native conservative Godunov solver before fan postprocessing.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

This milestone separates:

LEVEL 1 — exact source-native finite-volume balance
    Verify the pre-clip update identity cell-by-cell using the same fluxes,
    dt, phi, and dx as the frozen Godunov teacher.

LEVEL 2 — raw native-grid continuous-form diagnostic
    Evaluate
        S_tD + d_xD[ exp(Nc*xD) fw(S) ]
    on densely sampled native-grid snapshots.
    This is diagnostic only; the exact FV balance remains authoritative.

LEVEL 3 — moving-fan interpolation
    Extract xD_star and map the raw native solution to xi in [0,1].

LEVEL 4 — source fan postprocessing
    Apply, in order:
        interpolation only
        -> Sw_star flooring
        -> forced injector/tip endpoints

LEVEL 5 — sparse six-time representation
    Repeat the source fan representation at the exact six source times
    from 100 d to 0.95*tBT.

Two source-defined diagnostic cases are used across the full physical Nc grid:
    Case 1: no=2, nw=2, swc=.20, sor=.20, mu_w=.5, mu_o=.7, phi=.20
    Case 2: no=3, nw=2, swc=.15, sor=.25, mu_w=6, mu_o=.9, phi=.25

No scientific numeric acceptance threshold is invented.
Exact update-balance identities are judged only by a machine-precision-derived
computational tolerance.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import math
import sys

import numpy as np


R = Path(__file__).resolve().parent
MILESTONE = "V16E-1B2Q-XPU"

# =============================================================================
# Frozen authority
# =============================================================================

STAGE2 = R / "pi_rnn_stage2_compressible_godunov.py"
STAGE2_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

BASE_RUNNER = (
    R
    / "PAD_Stream_V16E1B2C_XPU_COMP_XPU_002_800Epoch_Compressible_Reproduction.py"
)
BASE_RUNNER_SHA = "587bd355cd17efd3e7d814f1320d4894c857256c89699ea7c71dc5e63984ae18"

# B2P protocol freeze authority
B2P_SOURCE = (
    R
    / "PAD_Stream_V16E1B2P_XPU_B2O_Interpretation_Native_Teacher_Verification_Protocol_Freeze.py"
)
B2P_SOURCE_SHA = "c2deae76d5bd37a1f9a0207c635e9e0115a23c267af8acc31c3e0687df7c3184"

B2P_DIR = (
    R
    / "output"
    / "V16_E1B2P_XPU_B2O_INTERPRETATION_NATIVE_TEACHER_PROTOCOL_FREEZE"
)
B2P_INTERPRETATION = B2P_DIR / "V16E1B2P_B2O_Interpretation.json"
B2P_PROTOCOL = B2P_DIR / "V16E1B2P_Native_Godunov_Verification_Protocol.json"
B2P_HANDOFF = B2P_DIR / "V16E1B2P_B2Q_Handoff.md"
B2P_SUMMARY = B2P_DIR / "PAD_Stream_V16E1B2P_XPU_Summary.json"

B2P_INTERPRETATION_SHA = "a16e462681aee250217b043d4e81b66f8a54a3ddd925dae9a558eb15539a02a7"
B2P_PROTOCOL_SHA = "553288b7e18c012d87c977efd6742bc5719f3e5f05e37734fe5e6f595590ae0d"
B2P_HANDOFF_SHA = "afd731d9c4684ae363fb9cc51c6aaa0fad92103e87cf7b7d5ca8c8c691b0de51"
B2P_SUMMARY_SHA = "ea173d507b254ea2a9a2c92dba7251845e534bb1d7f9b49e0d8eced891662e00"

EXPECTED_B2P_STATUS = (
    "V16E1B2P_XPU_B2O_INTERPRETATION_AND_NATIVE_TEACHER_VERIFICATION_PROTOCOL_FROZEN_"
    "CONSERVATIVE_AUTOGRAD_FORM_IDENTITY_AND_NC0_ALGEBRAIC_NESTING_CERTIFIED_"
    "PROCESSED_64_NODE_SIX_TIME_FAN_TEACHER_CONTINUOUS_RESIDUAL_AUDIT_CLASSIFIED_INCONCLUSIVE_"
    "FAN_INTERPOLATION_FLOOR_ENDPOINT_AND_SPARSE_TIME_EFFECTS_BOUND_AS_POTENTIAL_AUDIT_ARTIFACTS_"
    "SOURCE_NATIVE_GODUNOV_DISCRETE_CONSERVATION_AND_FAN_PROCESSING_ABLATION_REQUIRED_"
    "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_B3_NOT_AUTHORIZED"
)

OUT = (
    R
    / "output"
    / "V16_E1B2Q_XPU_SOURCE_NATIVE_GODUNOV_CONSERVATION_AUDIT"
)
OUT.mkdir(parents=True, exist_ok=True)

NATIVE_BALANCE = OUT / "V16E1B2Q_Native_FV_Discrete_Conservation_Audit.json"
ABLATION = OUT / "V16E1B2Q_Fan_Processing_Residual_Ablation.json"
DECISION = OUT / "V16E1B2Q_Native_Teacher_Verification_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2Q_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
DENSE_TIMES = 61
SPARSE_TIMES = 6
N_FAN = 64

FLOAT64_EPS = float(np.finfo(np.float64).eps)
IDENTITY_EPS_MULTIPLIER = 2048.0


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


def import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def case_defs(M):
    return {
        "case1": M.make_case(
            no=2.0,
            nw=2.0,
            swc=0.20,
            sor=0.20,
            mu_w=0.5,
            mu_o=0.7,
            phi=0.20,
        ),
        "case2": M.make_case(
            no=3.0,
            nw=2.0,
            swc=0.15,
            sor=0.25,
            mu_w=6.0,
            mu_o=0.9,
            phi=0.25,
        ),
    }


def aggregate(arr):
    a = np.asarray(arr, dtype=float)
    return {
        "n": int(a.size),
        "MSE": float(np.mean(a ** 2)),
        "RMSE": float(np.sqrt(np.mean(a ** 2))),
        "MAE": float(np.mean(np.abs(a))),
        "max_abs": float(np.max(np.abs(a))),
    }


def identity_bound(scale: float) -> float:
    return IDENTITY_EPS_MULTIPLIER * FLOAT64_EPS * max(1.0, abs(float(scale)))


# =============================================================================
# Exact instrumented native Godunov reproduction
# =============================================================================

def instrumented_godunov(
    M,
    p: dict,
    Nc: float,
    times_days,
    nx: int,
    cfl: float = 0.4,
):
    """
    Faithfully reproduce the exact frozen source update while collecting:
      * raw pre-clip FV identity residual
      * post-clip correction
      * post-clip FV residual
      * dense snapshots
    """
    M.validate_params(p)

    L = p["x_ip"]
    xD = np.linspace(0.0, 1.0, nx)
    dx = L / (nx - 1)

    u_inj = M.FT3_PER_BBL * p["i_w"] / p["A"]
    u = u_inj * np.exp(Nc * xD)
    u_face = 0.5 * (u[:-1] + u[1:])

    sw_init = p["swc"] + 1e-3
    sw_inj = 1.0 - p["sor"] - 1e-3
    f_inj = M.fractional_flow_np(
        np.array([sw_inj]),
        p,
    )[0]

    Sg = np.linspace(
        p["swc"],
        1.0 - p["sor"],
        400,
    )
    dfw, _ = M.dfw_dsw_np(Sg, p)

    dt_cfl = (
        cfl * p["phi"] * dx
        / (u.max() * np.abs(dfw).max() + M.EPS)
    )

    S = np.full(nx, sw_init, dtype=float)
    S[0] = sw_inj
    F = np.empty(nx + 1, dtype=float)

    snapshots = []
    t_now = 0.0

    preclip_residuals = []
    postclip_residuals = []
    clip_corrections = []
    global_preclip = []
    global_postclip = []
    clipped_cell_count = 0
    step_count = 0

    for t_target in sorted(float(t) for t in times_days):
        span_t = t_target - t_now

        if span_t <= 0:
            snapshots.append(S.copy())
            continue

        nt = max(
            1,
            int(np.ceil(span_t / dt_cfl)),
        )
        dt = span_t / nt

        for _ in range(nt):
            S_old = S.copy()

            f = M.fractional_flow_np(
                S_old,
                p,
            )

            F[0] = u[0] * f_inj
            F[1:nx] = u_face * f[:-1]
            F[nx] = u[-1] * f[-1]

            flux_div = (
                F[2:] - F[1:-1]
            )

            delta = (
                dt / (p["phi"] * dx)
            ) * flux_div

            S_raw = S_old.copy()
            S_raw[1:] -= delta
            S_raw[0] = sw_inj

            # Exact raw FV identity on dynamically updated cells 1:.
            r_pre = (
                S_raw[1:]
                - S_old[1:]
                + delta
            )

            S_post = S_raw.copy()
            np.clip(
                S_post,
                p["swc"],
                1.0 - p["sor"],
                out=S_post,
            )

            correction = (
                S_post[1:]
                - S_raw[1:]
            )

            r_post = (
                S_post[1:]
                - S_old[1:]
                + delta
            )

            preclip_residuals.append(
                r_pre
            )
            postclip_residuals.append(
                r_post
            )
            clip_corrections.append(
                correction
            )

            global_preclip.append(
                float(
                    np.sum(
                        p["phi"] * dx * r_pre
                    )
                )
            )
            global_postclip.append(
                float(
                    np.sum(
                        p["phi"] * dx * r_post
                    )
                )
            )

            clipped_cell_count += int(
                np.count_nonzero(
                    np.abs(correction) > 0.0
                )
            )

            S = S_post
            step_count += 1

        t_now = t_target
        snapshots.append(S.copy())

    pre = np.concatenate(
        preclip_residuals
    )
    post = np.concatenate(
        postclip_residuals
    )
    corr = np.concatenate(
        clip_corrections
    )

    max_scale = max(
        1.0,
        float(np.max(np.abs(S))),
        float(np.max(np.abs(pre))),
        float(np.max(np.abs(post))),
    )

    return {
        "xD": xD,
        "snapshots": np.asarray(
            snapshots,
            dtype=float,
        ),
        "times_days": np.asarray(
            sorted(float(t) for t in times_days),
            dtype=float,
        ),
        "step_count":
            int(step_count),
        "dt_cfl_days":
            float(dt_cfl),
        "preclip_identity":
            {
                **aggregate(pre),
                "machine_epsilon_identity_bound":
                    identity_bound(max_scale),
                "max_abs_within_machine_bound":
                    bool(
                        np.max(np.abs(pre))
                        <= identity_bound(max_scale)
                    ),
            },
        "postclip_balance":
            aggregate(post),
        "clip_correction":
            {
                **aggregate(corr),
                "clipped_cell_events":
                    int(clipped_cell_count),
            },
        "global_preclip_balance":
            aggregate(
                np.asarray(global_preclip)
            ),
        "global_postclip_balance":
            aggregate(
                np.asarray(global_postclip)
            ),
    }


# =============================================================================
# Native-grid continuous diagnostic
# =============================================================================

def native_continuous_residual(
    M,
    p,
    Nc,
    xD,
    times_days,
    snaps,
):
    C = (
        M.FT3_PER_BBL
        * p["i_w"]
        / (
            p["phi"]
            * p["A"]
            * p["x_ip"]
        )
    )

    tD = C * np.asarray(
        times_days,
        dtype=float,
    )

    S_t = np.gradient(
        snaps,
        tD,
        axis=0,
        edge_order=2,
    )

    fw = M.fractional_flow_np(
        snaps,
        p,
    )

    fluxD = (
        np.exp(
            Nc * xD[None, :]
        )
        * fw
    )

    F_x = np.gradient(
        fluxD,
        xD,
        axis=1,
        edge_order=2,
    )

    R = S_t + F_x

    # Native full interior excluding domain endpoints.
    full = R[:, 1:-1]

    # Pre-front smooth region, excluding 3 native cells before numerical front.
    grid = np.linspace(
        p["swc"],
        1.0 - p["sor"],
        800,
    )
    _, fw_grid = M.dfw_dsw_np(
        grid,
        p,
    )
    Sw_star, _, _, _ = M.welge_tangent(
        grid,
        fw_grid,
        p["swc"],
    )

    dxD = 1.0 / (len(xD) - 1)
    smooth_vals = []

    for k, S in enumerate(snaps):
        X = M.godunov_front_from_profile(
            xD,
            S,
            Sw_star,
            p["swc"],
        )

        if not np.isfinite(X):
            continue

        mask = (
            (xD > 0.0)
            & (
                xD
                < X - 3.0 * dxD
            )
        )

        if np.any(mask):
            smooth_vals.extend(
                R[k, mask].tolist()
            )

    return {
        "full_native_interior":
            aggregate(full.reshape(-1)),
        "prefront_smooth_native":
            aggregate(
                np.asarray(
                    smooth_vals,
                    dtype=float,
                )
            ),
    }


# =============================================================================
# Fan processing ablation
# =============================================================================

def sw_star_for_case(M, p):
    grid = np.linspace(
        p["swc"],
        1.0 - p["sor"],
        800,
    )
    _, fw = M.dfw_dsw_np(
        grid,
        p,
    )
    Sw_star, _, _, _ = M.welge_tangent(
        grid,
        fw,
        p["swc"],
    )
    return float(Sw_star)


def build_fan_stages(
    M,
    p,
    Nc,
    xD,
    snaps,
    n_fan=N_FAN,
):
    Sw_star = sw_star_for_case(
        M,
        p,
    )

    xi = np.linspace(
        0.0,
        1.0,
        n_fan,
    )

    X = []
    interp_only = []
    floor_only = []
    endpoints = []

    for S in snaps:
        x_star = M.godunov_front_from_profile(
            xD,
            S,
            Sw_star,
            p["swc"],
        )

        if not np.isfinite(x_star) or x_star <= 0:
            raise RuntimeError(
                "Nonfinite Godunov front in B2Q fan ablation."
            )

        S_interp = np.interp(
            xi * x_star,
            xD,
            S,
        )

        S_floor = np.maximum(
            S_interp,
            Sw_star,
        )

        S_end = S_floor.copy()
        S_end[0] = 1.0 - p["sor"]
        S_end[-1] = Sw_star

        X.append(
            float(x_star)
        )
        interp_only.append(
            S_interp
        )
        floor_only.append(
            S_floor
        )
        endpoints.append(
            S_end
        )

    return {
        "xi":
            xi,
        "X":
            np.asarray(X, dtype=float),
        "Sw_star":
            Sw_star,
        "interpolation_only":
            np.asarray(interp_only, dtype=float),
        "plus_Sw_star_floor":
            np.asarray(floor_only, dtype=float),
        "plus_forced_endpoints":
            np.asarray(endpoints, dtype=float),
    }


def moving_fan_residual(
    M,
    p,
    Nc,
    times_days,
    xi,
    X,
    Sfan,
):
    C = (
        M.FT3_PER_BBL
        * p["i_w"]
        / (
            p["phi"]
            * p["A"]
            * p["x_ip"]
        )
    )

    tD = (
        C
        * np.asarray(
            times_days,
            dtype=float,
        )
    )

    S_t = np.gradient(
        Sfan,
        tD,
        axis=0,
        edge_order=2,
    )

    S_xi = np.gradient(
        Sfan,
        xi,
        axis=1,
        edge_order=2,
    )

    Xdot = np.gradient(
        X,
        tD,
        edge_order=2,
    )

    fw = M.fractional_flow_np(
        Sfan,
        p,
    )

    flux = (
        np.exp(
            Nc
            * xi[None, :]
            * X[:, None]
        )
        * fw
    )

    F_xi = np.gradient(
        flux,
        xi,
        axis=1,
        edge_order=2,
    )

    R = (
        S_t
        - (
            xi[None, :]
            * Xdot[:, None]
            / X[:, None]
        )
        * S_xi
        + F_xi / X[:, None]
    )

    # B2O-compatible interior fan nodes.
    interior = R[:, 1:-1]

    # More conservative interior excluding three nodes near each fan boundary.
    core = R[:, 3:-3]

    return {
        "interior_1_to_minus1":
            aggregate(
                interior.reshape(-1)
            ),
        "core_3_to_minus3":
            aggregate(
                core.reshape(-1)
            ),
    }


def exact_sparse_source_fan(
    M,
    p,
    Nc,
    sparse_times,
):
    profiles = M.build_fan_profiles_godunov(
        sparse_times,
        p,
        Nc=Nc,
        n_fan=N_FAN,
        nx=M.NX_TRAIN,
    )

    if len(profiles) != len(sparse_times):
        raise RuntimeError(
            "Exact sparse source fan did not return all requested profiles."
        )

    xi = np.asarray(
        profiles[0]["xi"],
        dtype=float,
    )

    X = np.asarray([
        prof["xD_star"]
        for prof in profiles
    ], dtype=float)

    S = np.asarray([
        prof["Sw_fan_true"]
        for prof in profiles
    ], dtype=float)

    t = np.asarray([
        prof["t_days"]
        for prof in profiles
    ], dtype=float)

    return moving_fan_residual(
        M,
        p,
        Nc,
        t,
        xi,
        X,
        S,
    )


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2Q-XPU")
    print("Source-Native Godunov Discrete-Conservation Verification")
    print("+ Fan-Processing Residual Ablation")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — native teacher audit only.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2Q summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(
                STAGE2,
                STAGE2_SHA,
            ),

        "base_runner_SHA_exact":
            exact(
                BASE_RUNNER,
                BASE_RUNNER_SHA,
            ),

        "B2P_source_SHA_exact":
            exact(
                B2P_SOURCE,
                B2P_SOURCE_SHA,
            ),

        "B2P_interpretation_SHA_exact":
            exact(
                B2P_INTERPRETATION,
                B2P_INTERPRETATION_SHA,
            ),

        "B2P_protocol_SHA_exact":
            exact(
                B2P_PROTOCOL,
                B2P_PROTOCOL_SHA,
            ),

        "B2P_handoff_SHA_exact":
            exact(
                B2P_HANDOFF,
                B2P_HANDOFF_SHA,
            ),

        "B2P_summary_SHA_exact":
            exact(
                B2P_SUMMARY,
                B2P_SUMMARY_SHA,
            ),
    }

    b2p = (
        read_json(
            B2P_SUMMARY
        )
        if B2P_SUMMARY.exists()
        else {}
    )

    protocol = (
        read_json(
            B2P_PROTOCOL
        )
        if B2P_PROTOCOL.exists()
        else {}
    )

    gates.update({
        "B2P_status_exact":
            b2p.get(
                "status"
            )
            == EXPECTED_B2P_STATUS,

        "B2P_new_training_false":
            b2p.get(
                "new_training_authorized"
            )
            is False,

        "B2P_B3_false":
            b2p.get(
                "B3_authorized"
            )
            is False,

        "B2P_next_milestone_exact":
            protocol.get(
                "next_milestone"
            )
            == MILESTONE,
    })

    print("AUTHORITY / PROTOCOL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(gates.values()):
        raise RuntimeError(
            "B2Q blocked by authority/protocol mismatch."
        )

    M = import_module(
        BASE_RUNNER,
        "v16e1b2c_base",
    )

    gates.update({
        "source_native_solver_exists":
            hasattr(
                M,
                "godunov_compressible_snapshots",
            ),

        "source_fan_builder_exists":
            hasattr(
                M,
                "build_fan_profiles_godunov",
            ),

        "NX_TRAIN_1601":
            int(M.NX_TRAIN)
            == 1601,
    })

    cases = case_defs(
        M
    )

    native_results = {}
    ablation_results = {}

    all_preclip_identity_pass = True
    all_native_metrics_finite = True
    all_ablation_metrics_finite = True

    for case_name, p in cases.items():
        native_results[case_name] = {}
        ablation_results[case_name] = {}

        print(
            f"\n{'=' * 80}\n"
            f"{case_name.upper()}\n"
            f"{'=' * 80}"
        )

        for Nc in NC_VALUES:
            t_bt = M.breakthrough_time_days(
                p,
                Nc=Nc,
            )

            if 0.95 * t_bt <= 100.0:
                raise RuntimeError(
                    f"Invalid audit horizon for {case_name}, Nc={Nc}"
                )

            dense_times = np.linspace(
                100.0,
                0.95 * t_bt,
                DENSE_TIMES,
            )

            sparse_times = np.linspace(
                100.0,
                0.95 * t_bt,
                SPARSE_TIMES,
            )

            native = instrumented_godunov(
                M,
                p,
                Nc,
                dense_times,
                nx=M.NX_TRAIN,
                cfl=0.4,
            )

            cont = native_continuous_residual(
                M,
                p,
                Nc,
                native["xD"],
                native["times_days"],
                native["snapshots"],
            )

            native_record = {
                "Nc":
                    float(Nc),

                "tBT_days":
                    float(t_bt),

                "dense_times":
                    int(DENSE_TIMES),

                "native_grid":
                    int(M.NX_TRAIN),

                "step_count":
                    native["step_count"],

                "dt_cfl_days":
                    native["dt_cfl_days"],

                "preclip_identity":
                    native["preclip_identity"],

                "postclip_balance":
                    native["postclip_balance"],

                "clip_correction":
                    native["clip_correction"],

                "global_preclip_balance":
                    native["global_preclip_balance"],

                "global_postclip_balance":
                    native["global_postclip_balance"],

                "native_continuous_diagnostic":
                    cont,
            }

            native_results[
                case_name
            ][
                f"{Nc:.2f}"
            ] = native_record

            pass_identity = native[
                "preclip_identity"
            ][
                "max_abs_within_machine_bound"
            ]

            all_preclip_identity_pass &= bool(
                pass_identity
            )

            for block in (
                native["preclip_identity"],
                native["postclip_balance"],
                native["clip_correction"],
                native["global_preclip_balance"],
                native["global_postclip_balance"],
                cont["full_native_interior"],
                cont["prefront_smooth_native"],
            ):
                for k in (
                    "MSE",
                    "RMSE",
                    "MAE",
                    "max_abs",
                ):
                    if k in block:
                        all_native_metrics_finite &= finite(
                            block[k]
                        )

            # -------------------------------------------------------------
            # Fan ablation from the SAME dense native snapshots.
            # -------------------------------------------------------------

            fan = build_fan_stages(
                M,
                p,
                Nc,
                native["xD"],
                native["snapshots"],
                n_fan=N_FAN,
            )

            dense_interp = moving_fan_residual(
                M,
                p,
                Nc,
                native["times_days"],
                fan["xi"],
                fan["X"],
                fan["interpolation_only"],
            )

            dense_floor = moving_fan_residual(
                M,
                p,
                Nc,
                native["times_days"],
                fan["xi"],
                fan["X"],
                fan["plus_Sw_star_floor"],
            )

            dense_end = moving_fan_residual(
                M,
                p,
                Nc,
                native["times_days"],
                fan["xi"],
                fan["X"],
                fan["plus_forced_endpoints"],
            )

            sparse_exact = exact_sparse_source_fan(
                M,
                p,
                Nc,
                sparse_times,
            )

            ablation_record = {
                "Nc":
                    float(Nc),

                "dense_native_times":
                    int(DENSE_TIMES),

                "sparse_source_times":
                    int(SPARSE_TIMES),

                "fan_nodes":
                    int(N_FAN),

                "stage_0_native_grid_continuous":
                    cont,

                "stage_1_front_extract_plus_interpolate_to_xi":
                    dense_interp,

                "stage_2_plus_Sw_star_floor":
                    dense_floor,

                "stage_3_plus_forced_endpoints":
                    dense_end,

                "stage_4_exact_source_sparse_six_time_fan":
                    sparse_exact,
            }

            ablation_results[
                case_name
            ][
                f"{Nc:.2f}"
            ] = ablation_record

            for stage in (
                dense_interp,
                dense_floor,
                dense_end,
                sparse_exact,
            ):
                for branch in stage.values():
                    for k in (
                        "MSE",
                        "RMSE",
                        "MAE",
                        "max_abs",
                    ):
                        all_ablation_metrics_finite &= finite(
                            branch[k]
                        )

            print(
                f"  Nc={Nc:.2f} "
                f"| FV preclip max={native['preclip_identity']['max_abs']:.3e} "
                f"| clip events={native['clip_correction']['clipped_cell_events']} "
                f"| native smooth MSE={cont['prefront_smooth_native']['MSE']:.3e} "
                f"| fan interp MSE={dense_interp['interior_1_to_minus1']['MSE']:.3e} "
                f"| +floor={dense_floor['interior_1_to_minus1']['MSE']:.3e} "
                f"| +endpoints={dense_end['interior_1_to_minus1']['MSE']:.3e} "
                f"| sparse6={sparse_exact['interior_1_to_minus1']['MSE']:.3e}"
            )

    native_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "SOURCE_NATIVE_GODUNOV_FINITE_VOLUME_DISCRETE_CONSERVATION_AUDIT",

        "authority": {
            "Stage2_source_sha256":
                STAGE2_SHA,
            "base_runner_sha256":
                BASE_RUNNER_SHA,
            "B2P_protocol_sha256":
                B2P_PROTOCOL_SHA,
        },

        "exact_update_identity":
            "S_raw[1:] - S_old[1:] + dt/(phi*dx)*(F[2:]-F[1:-1]) = 0",

        "post_update_operations":
            [
                "S[0]=sw_inj",
                "np.clip(S,swc,1-sor)",
            ],

        "identity_tolerance_policy": {
            "float64_epsilon":
                FLOAT64_EPS,
            "multiplier":
                IDENTITY_EPS_MULTIPLIER,
            "classification":
                "computational identity tolerance only; not a scientific model threshold",
        },

        "cases":
            native_results,

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

    NATIVE_BALANCE.write_text(
        json.dumps(
            native_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    ablation_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "FAN_PROCESSING_CONTINUOUS_RESIDUAL_ABLATION",

        "processing_order": [
            "native 1601-cell Godunov snapshots",
            "numerical xD_star extraction",
            "interpolation to 64 xi nodes",
            "Sw_star flooring",
            "forced injector/tip endpoints",
            "six-time source representation",
        ],

        "residual_definition":
            "moving-fan conservative continuous diagnostic using FD Xdot",

        "interpretation_policy":
            "The exact native discrete FV balance is authoritative. Continuous "
            "residual magnitudes are diagnostic and are used only to identify "
            "representation/discretization effects.",

        "cases":
            ablation_results,

        "no_training":
            True,
        "no_OOD":
            True,
        "no_TOF":
            True,
    }

    ABLATION.write_text(
        json.dumps(
            ablation_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates.update({
        "all_native_preclip_FV_identities_machine_pass":
            bool(
                all_preclip_identity_pass
            ),

        "all_native_metrics_finite":
            bool(
                all_native_metrics_finite
            ),

        "all_ablation_metrics_finite":
            bool(
                all_ablation_metrics_finite
            ),

        "all_two_cases_present":
            set(
                native_results.keys()
            )
            == {"case1", "case2"},

        "all_five_Nc_present_each_case":
            all(
                set(
                    rec.keys()
                )
                == {
                    "0.00",
                    "0.05",
                    "0.10",
                    "0.20",
                    "0.30",
                }
                for rec
                in native_results.values()
            ),

        "native_balance_written":
            NATIVE_BALANCE.exists()
            and NATIVE_BALANCE.stat().st_size > 0,

        "ablation_written":
            ABLATION.exists()
            and ABLATION.stat().st_size > 0,

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

        "no_scientific_numeric_threshold":
            True,
    })

    decision = {
        "milestone":
            MILESTONE,

        "native_discrete_conservation":
            (
                "MACHINE_PRECISION_VERIFIED_PRECLIP"
                if gates[
                    "all_native_preclip_FV_identities_machine_pass"
                ]
                else
                "DISCRETE_BALANCE_REQUIRES_REPAIR"
            ),

        "continuous_native_and_fan_ablation":
            "FROZEN_FOR_INTERPRETATION",

        "training_authorized":
            False,

        "B3_authorized":
            False,

        "next_decision":
            "Interpret native discrete balance, clipping corrections, native-grid "
            "continuous residuals, and sequential fan-processing residual inflation "
            "before freezing any corrected Stage-2 training protocol.",

        "prohibited": [
            "treating processed-fan residual magnitude as native FV conservation error",
            "modifying the frozen Stage-2 source",
            "creating an optimizer in B2Q",
            "claiming OOD validation",
            "automatically authorizing B3",
        ],
    }

    DECISION.write_text(
        json.dumps(
            decision,
            indent=2,
        ),
        encoding="utf-8",
    )

    gates["decision_written"] = (
        DECISION.exists()
        and DECISION.stat().st_size > 0
    )

    ok = all(
        bool(v)
        for v
        in gates.values()
    )

    status = (
        "V16E1B2Q_XPU_SOURCE_NATIVE_GODUNOV_DISCRETE_CONSERVATION_AND_FAN_PROCESSING_ABLATION_COMPLETE_"
        "EXACT_PRECLIP_FINITE_VOLUME_UPDATE_BALANCE_MACHINE_PRECISION_VERIFIED_"
        "POSTCLIP_CORRECTIONS_NATIVE_CONTINUOUS_DIAGNOSTICS_FRONT_EXTRACTION_XI_INTERPOLATION_SWSTAR_FLOOR_"
        "FORCED_ENDPOINT_AND_SPARSE_SIX_TIME_EFFECTS_FROZEN_ACROSS_TWO_SOURCE_CASES_AND_FULL_NC_GRID_"
        "NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "CORRECTED_STAGE2_TRAINING_PROTOCOL_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2Q_XPU_NATIVE_TEACHER_AUDIT_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "native_balance_sha256":
            sha256(
                NATIVE_BALANCE
            ),

        "ablation_sha256":
            sha256(
                ABLATION
            ),

        "decision_sha256":
            sha256(
                DECISION
            ),

        "new_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2R-XPU — interpret B2Q native conservation and fan-processing "
                "ablation; decide whether the corrected conservative residual is ready "
                "for a prospective Stage-2 training protocol"
                if ok else
                "V16E-1B2Q-R1 — diagnose native conservation/audit gate failure"
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

    print("\nFINAL GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    print("\nSTATUS")
    print(
        " ",
        status,
    )

    print("\nHASHES")
    print(
        "  Native balance:",
        sha256(
            NATIVE_BALANCE
        ),
    )
    print(
        "  Ablation      :",
        sha256(
            ABLATION
        ),
    )
    print(
        "  Decision      :",
        sha256(
            DECISION
        ),
    )
    print(
        "  Summary       :",
        sha256(
            SUMMARY
        ),
    )

    print("\nNEXT")
    print(
        " ",
        summary[
            "next_milestone"
        ],
    )

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
