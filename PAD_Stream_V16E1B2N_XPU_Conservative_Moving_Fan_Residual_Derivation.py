#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2N-XPU
Conservative Stage-2 Moving-Fan Residual Derivation + Front-Speed Closure Audit

Purpose
-------
Freeze the mathematically consistent conservative Stage-2 residual in the
moving fan coordinate

    xi = xD / X(tD),   X(tD) = xD_star(tD),

and audit the front-speed closure against the exact frozen Godunov fan dataset.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Frozen physical conservative equation
-------------------------------------
The Stage-2 Godunov teacher solves, after the source's xD/tD nondimensionalization,

    dS/dtD |_xD + d[ uD(xD) * fw(S) ]/dxD = 0

with

    uD(xD) = exp(Nc*xD).

Moving fan coordinate
---------------------
Let

    X(tD) = xD_star(tD)
    xi    = xD / X(tD)
    s(xi,tD) = S(xD,tD).

Then

    dxi/dtD |_xD = -xi * Xdot / X
    d/dxD = (1/X) d/dxi

and therefore

    s_t|xi - (xi*Xdot/X) s_xi
    + (1/X) d/dxi [ exp(Nc*xi*X) fw(s) ] = 0.

Network-conditioning chain rule
-------------------------------
The frozen PI-RNN conditioner contains tD and X=xD_star as separate inputs.
Writing the network as

    N = N(xi, tD, X, other_fixed_case_parameters),

the physical derivative along one case at fixed xi is

    ds/dtD|xi = N_tD + Xdot * N_X,

because X=X(tD). Thus the implementable conservative residual is

    R_cons =
        N_tD
        + Xdot*N_X
        - (xi*Xdot/X)*N_xi
        + (1/X) d/dxi [ exp(Nc*xi*X) fw(N) ].

Expanded equivalent:

    R_cons =
        N_tD
        + Xdot*N_X
        + [ exp(Nc*xi*X)*fw'(N)/X - xi*Xdot/X ] * N_xi
        + Nc*exp(Nc*xi*X)*fw(N).

Front-speed closure
-------------------
For the conservative flux F(xD,S)=exp(Nc*xD) fw(S), the local
Rankine-Hugoniot condition at X gives

    Xdot =
        exp(Nc*X)
        * [fw(S_L)-fw(S_R)] / [S_L-S_R].

For the frozen fan convention:

    S_L = Sw_star
    S_R = swc

so

    sigma_BL = [fw(Sw_star)-fw(swc)]/(Sw_star-swc)
    Xdot_RH  = exp(Nc*X) * sigma_BL.

This is also identical to differentiating the source's transformed shock
relation y(X;Nc)=tD*sigma_BL.

Audit
-----
The frozen dataset contains six Godunov fan snapshots per sampled physical
case/Nc combination. This script groups profiles by the fixed physical
parameters, computes finite-difference dX/dtD from the stored mid-jump
Godunov fronts, and compares it with Xdot_RH.

No numerical pass/fail threshold is introduced. The audit is descriptive and
is intended to determine how accurately the physical RH closure tracks the
finite-resolution mid-jump front used by the frozen teacher.
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
MILESTONE = "V16E-1B2N-XPU"

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

DATASET = (
    R / "output" / "V16_E1B_XPU_DATASETS"
    / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
)
DATASET_SHA = "46f10f00ff6dc48f7b2b936bd7d602e6435f72f8410138c5aad0dd4add555f1c"

# B2M reconciliation authority
B2M_SOURCE = (
    R
    / "PAD_Stream_V16E1B2M_XPU_Stage2_Physics_Objective_Reconciliation_Freeze.py"
)
B2M_SOURCE_SHA = "99285587de9d4e909ac2c5a7aba9fd090f387f4d6c61c13c6afb4e344a60836d"

B2M_DIR = (
    R / "output"
    / "V16_E1B2M_XPU_STAGE2_PHYSICS_OBJECTIVE_RECONCILIATION_FREEZE"
)
B2M_INTERPRETATION = B2M_DIR / "V16E1B2M_Stage2_Physics_Objective_Reconciliation.json"
B2M_BRANCHES = B2M_DIR / "V16E1B2M_Stage2_Branch_Roles.json"
B2M_HANDOFF = B2M_DIR / "V16E1B2M_Conservative_Residual_Design_Handoff.md"
B2M_SUMMARY = B2M_DIR / "PAD_Stream_V16E1B2M_XPU_Summary.json"

B2M_INTERPRETATION_SHA = "dc075e50040b14591fc0b98148865414499a820059a94fb14cf0c091f564611b"
B2M_BRANCHES_SHA = "1caac196fed47967407cdfade049278f8d947434895d9d025680c6349d9a6f75"
B2M_HANDOFF_SHA = "c16059c34821cbc3cb0328d750a086652ba3cb02f7b55e15c897d0992011f543"
B2M_SUMMARY_SHA = "a7a619e7688066f1b844669ba4441cb5c44bb21a8258fdceae64cc2070f6b53f"

EXPECTED_B2M_STATUS = (
    "V16E1B2M_XPU_STAGE2_PHYSICS_OBJECTIVE_RECONCILIATION_FROZEN_"
    "CONSERVATIVE_GODUNOV_TEACHER_AND_RETAINED_CHARACTERISTIC_RESIDUAL_INCOMPATIBILITY_CONFIRMED_FOR_POSITIVE_NC_"
    "SOURCE_FAITHFUL_STAGE2_LINEAGE_PRESERVED_COMP_XPU_004_BEST_ACCURACY_BRANCH_PRESERVED_"
    "NO_FURTHER_HYPERPARAMETER_TUNING_UNDER_INCOMPATIBLE_RESIDUAL_"
    "CONSERVATIVE_MOVING_FAN_COORDINATE_RESIDUAL_DERIVATION_REQUIRED_BEFORE_NEW_TRAINING_"
    "NO_OOD_NO_TOF_B3_NOT_YET_AUTHORIZED"
)

OUT = (
    R / "output"
    / "V16_E1B2N_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_DERIVATION"
)
OUT.mkdir(parents=True, exist_ok=True)

DERIVATION = OUT / "V16E1B2N_Conservative_Moving_Fan_Residual_Derivation.json"
FRONT_AUDIT = OUT / "V16E1B2N_Godunov_Front_Speed_Closure_Audit.json"
HANDOFF = OUT / "V16E1B2N_Residual_Implementation_Handoff.md"
SUMMARY = OUT / "PAD_Stream_V16E1B2N_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]


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


def group_key(row: np.ndarray):
    """
    Physical case + Nc identity.

    p11 =
      [no,nw,swi,sor,mu_w,mu_o,phi,tD,xD_star,Sw_star,Nc]

    tD and xD_star vary with snapshot time and are excluded.
    Sw_star is derived from the fixed rock/fluid parameters and is also excluded
    from the identity to avoid unnecessary float-key duplication.
    """
    cols = [0, 1, 2, 3, 4, 5, 6, 10]
    return tuple(float(row[i]) for i in cols)


def make_p_from_row(M, row: np.ndarray):
    return M.make_case(
        no=float(row[0]),
        nw=float(row[1]),
        swc=float(row[2]),
        sor=float(row[3]),
        mu_w=float(row[4]),
        mu_o=float(row[5]),
        phi=float(row[6]),
    )


def rh_speed(M, row: np.ndarray, X: np.ndarray):
    p = make_p_from_row(M, row)

    swc = float(row[2])
    Sw_star = float(row[9])
    Nc = float(row[10])

    fw_pair = M.fractional_flow_np(
        np.asarray([swc, Sw_star], dtype=float),
        p,
    )

    fw_r = float(fw_pair[0])
    fw_l = float(fw_pair[1])

    sigma = (
        (fw_l - fw_r)
        / max(Sw_star - swc, 1e-30)
    )

    return np.exp(Nc * X) * sigma, sigma


def audit_front_speeds(M, p11: np.ndarray):
    groups = {}

    for i, row in enumerate(p11):
        groups.setdefault(group_key(row), []).append(i)

    records = []
    per_nc = {
        f"{nc:.2f}": {
            "groups": 0,
            "points": 0,
            "abs_errors": [],
            "rel_errors": [],
            "empirical": [],
            "RH": [],
        }
        for nc in NC_VALUES
    }

    bad_groups = 0

    for key, ids in groups.items():
        ids = np.asarray(ids, dtype=int)
        rows = p11[ids]

        order = np.argsort(rows[:, 7])
        rows = rows[order]

        tD = rows[:, 7].astype(float)
        X = rows[:, 8].astype(float)
        Nc = float(rows[0, 10])

        if len(rows) < 3:
            bad_groups += 1
            continue

        # A group should represent one fixed physical case + Nc.
        if not np.all(np.diff(tD) > 0.0):
            bad_groups += 1
            continue

        # Finite-difference derivative of the finite-resolution mid-jump front.
        Xdot_fd = np.gradient(
            X,
            tD,
            edge_order=2 if len(X) >= 3 else 1,
        )

        Xdot_rh, sigma = rh_speed(
            M,
            rows[0],
            X,
        )

        err = Xdot_fd - Xdot_rh
        relerr = err / np.maximum(
            np.abs(Xdot_rh),
            1e-30,
        )

        nc_key = f"{Nc:.2f}"

        if nc_key not in per_nc:
            # Dataset authority should prevent this.
            raise RuntimeError(
                f"Unexpected physical Nc={Nc}"
            )

        per_nc[nc_key]["groups"] += 1
        per_nc[nc_key]["points"] += len(X)
        per_nc[nc_key]["abs_errors"].extend(
            np.abs(err).tolist()
        )
        per_nc[nc_key]["rel_errors"].extend(
            np.abs(relerr).tolist()
        )
        per_nc[nc_key]["empirical"].extend(
            Xdot_fd.tolist()
        )
        per_nc[nc_key]["RH"].extend(
            Xdot_rh.tolist()
        )

        records.append({
            "Nc": Nc,
            "n_snapshots": int(len(X)),
            "tD_min": float(tD.min()),
            "tD_max": float(tD.max()),
            "X_min": float(X.min()),
            "X_max": float(X.max()),
            "sigma_BL": float(sigma),
            "fd_speed_mean": float(np.mean(Xdot_fd)),
            "RH_speed_mean": float(np.mean(Xdot_rh)),
            "MAE_speed": float(np.mean(np.abs(err))),
            "mean_abs_relative_error":
                float(np.mean(np.abs(relerr))),
        })

    summary = {}

    for nc_key, rec in per_nc.items():
        ae = np.asarray(rec.pop("abs_errors"), dtype=float)
        re = np.asarray(rec.pop("rel_errors"), dtype=float)
        empirical = np.asarray(rec.pop("empirical"), dtype=float)
        rh = np.asarray(rec.pop("RH"), dtype=float)

        if len(ae) == 0:
            raise RuntimeError(
                f"No front-speed audit points for Nc={nc_key}"
            )

        summary[nc_key] = {
            "groups": int(rec["groups"]),
            "points": int(rec["points"]),
            "empirical_speed_mean": float(np.mean(empirical)),
            "RH_speed_mean": float(np.mean(rh)),
            "MAE_speed": float(np.mean(ae)),
            "RMSE_speed": float(
                np.sqrt(np.mean((empirical - rh) ** 2))
            ),
            "mean_abs_relative_error":
                float(np.mean(re)),
            "median_abs_relative_error":
                float(np.median(re)),
            "p95_abs_relative_error":
                float(np.quantile(re, 0.95)),
        }

    return {
        "group_count":
            int(len(groups)),
        "invalid_or_short_groups":
            int(bad_groups),
        "per_Nc":
            summary,
        "sample_group_records":
            records[:25],
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2N-XPU")
    print("Conservative Moving-Fan Residual Derivation + Front-Speed Closure Audit")
    print("=" * 80)
    print("DERIVATION / AUDIT ONLY — NO TRAINING.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2N summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),

        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),

        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "B2M_source_SHA_exact":
            exact(B2M_SOURCE, B2M_SOURCE_SHA),

        "B2M_interpretation_SHA_exact":
            exact(
                B2M_INTERPRETATION,
                B2M_INTERPRETATION_SHA,
            ),

        "B2M_branch_roles_SHA_exact":
            exact(
                B2M_BRANCHES,
                B2M_BRANCHES_SHA,
            ),

        "B2M_handoff_SHA_exact":
            exact(
                B2M_HANDOFF,
                B2M_HANDOFF_SHA,
            ),

        "B2M_summary_SHA_exact":
            exact(
                B2M_SUMMARY,
                B2M_SUMMARY_SHA,
            ),
    }

    b2m = read_json(
        B2M_SUMMARY
    ) if B2M_SUMMARY.exists() else {}

    gates.update({
        "B2M_status_exact":
            b2m.get("status")
            == EXPECTED_B2M_STATUS,

        "B2M_new_training_false":
            b2m.get(
                "new_training_authorized"
            )
            is False,

        "B2M_B3_false":
            b2m.get(
                "B3_authorized"
            )
            is False,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print(
            "[PASS]" if v else "[FAIL]",
            k,
        )

    if not all(gates.values()):
        raise RuntimeError(
            "B2N blocked by artifact authority mismatch."
        )

    M = import_module(
        BASE_RUNNER,
        "v16e1b2c_base",
    )

    d = np.load(DATASET)
    p11 = d["p11"]

    gates.update({
        "dataset_p11_shape_exact":
            tuple(p11.shape)
            == (14400, 11),

        "physical_Nc_min_0":
            np.isclose(
                float(np.min(p11[:, 10])),
                0.0,
                atol=1e-7,
            ),

        "physical_Nc_max_0p30":
            np.isclose(
                float(np.max(p11[:, 10])),
                0.30,
                atol=1e-7,
            ),
    })

    # -------------------------------------------------------------------------
    # Freeze derivation.
    # -------------------------------------------------------------------------

    derivation = {
        "milestone":
            MILESTONE,

        "classification":
            "CONSERVATIVE_STAGE2_MOVING_FAN_COORDINATE_RESIDUAL_DERIVATION",

        "source_coordinates": {
            "xD":
                "x / L",
            "tD":
                "(u_inj/(phi*L))*t",
            "uD":
                "u/u_inj = exp(Nc*xD)",
        },

        "physical_conservative_equation":
            "S_tD|xD + d_xD[ exp(Nc*xD)*fw(S) ] = 0",

        "moving_coordinate": {
            "X":
                "xD_star(tD)",
            "xi":
                "xD / X(tD)",
            "xD":
                "xi*X(tD)",
        },

        "coordinate_chain_rule": {
            "dxi_dtD_at_fixed_xD":
                "-xi*Xdot/X",
            "d_dxD":
                "(1/X)*d_dxi",
            "S_tD_at_fixed_xD":
                "s_tD_at_fixed_xi - (xi*Xdot/X)*s_xi",
        },

        "exact_moving_coordinate_PDE":
            "s_tD|xi - (xi*Xdot/X)*s_xi "
            "+ (1/X)*d_dxi[exp(Nc*xi*X)*fw(s)] = 0",

        "network_parameterization": {
            "network":
                "N(xi, tD, X, fixed_case_parameters)",
            "conditioner_dynamic_entries":
                ["tD", "xD_star"],
            "conditioner_fixed_along_one_case":
                [
                    "no", "nw", "swi", "sor",
                    "mu_w", "mu_o", "phi",
                    "Sw_star", "Nc",
                ],
            "total_time_derivative_at_fixed_xi":
                "dN/dtD|xi = N_tD + Xdot*N_X",
        },

        "implementable_conservative_residual_conservative_form":
            "R_cons = N_tD + Xdot*N_X "
            "- (xi*Xdot/X)*N_xi "
            "+ (1/X)*d_dxi[exp(Nc*xi*X)*fw(N)]",

        "implementable_conservative_residual_expanded_form":
            "R_cons = N_tD + Xdot*N_X "
            "+ [exp(Nc*xi*X)*fw'(N)/X - xi*Xdot/X]*N_xi "
            "+ Nc*exp(Nc*xi*X)*fw(N)",

        "front_speed_closure": {
            "Rankine_Hugoniot_general":
                "Xdot = exp(Nc*X) * "
                "[fw(S_L)-fw(S_R)]/[S_L-S_R]",

            "frozen_fan_states":
                {
                    "S_L":
                        "Sw_star",
                    "S_R":
                        "swc",
                },

            "sigma_BL":
                "[fw(Sw_star)-fw(swc)]/(Sw_star-swc)",

            "Xdot_RH":
                "exp(Nc*X)*sigma_BL",

            "transform_identity":
                "Differentiating y(X;Nc)=tD*sigma_BL with "
                "dy/dX=exp(-Nc*X) gives the same "
                "Xdot=exp(Nc*X)*sigma_BL.",
        },

        "Nc0_limit": {
            "uD":
                1.0,
            "Xdot":
                "sigma_BL",
            "PDE":
                "the standard conservative incompressible BL equation "
                "expressed in the same moving fan coordinate",
        },

        "implementation_requirements": [
            "Differentiate network output with respect to xi.",
            "Differentiate network output with respect to conditioner tD.",
            "Differentiate network output with respect to conditioner xD_star.",
            "Include Xdot*N_X in the physical time derivative.",
            "Include the moving-grid advection term -xi*Xdot/X*N_xi.",
            "Use physical raw Nc, never scaled Nc.",
            "Use the exact fractional-flow implementation bound to Stage 2.",
            "Use interior fan nodes for residual evaluation; do not enforce "
            "pointwise smooth-PDE residual across the shock discontinuity.",
            "Validate analytical/autograd conservative-form and expanded-form "
            "residuals against each other before training.",
        ],

        "training_authorized":
            False,

        "B3_authorized":
            False,
    }

    DERIVATION.write_text(
        json.dumps(
            derivation,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Front speed audit.
    # -------------------------------------------------------------------------

    print("\nGODUNOV FRONT-SPEED CLOSURE AUDIT")

    front = audit_front_speeds(
        M,
        p11,
    )

    for nc, rec in front["per_Nc"].items():
        print(
            f"  Nc={nc} "
            f"| groups={rec['groups']} "
            f"| points={rec['points']} "
            f"| FD mean={rec['empirical_speed_mean']:.6e} "
            f"| RH mean={rec['RH_speed_mean']:.6e} "
            f"| MAE={rec['MAE_speed']:.6e} "
            f"| mean |rel|={rec['mean_abs_relative_error']:.4f}"
        )

    front_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "FROZEN_GODUNOV_MIDJUMP_FRONT_VS_RANKINE_HUGONIOT_SPEED_AUDIT",

        "dataset_sha256":
            DATASET_SHA,

        "front_definition":
            "frozen Godunov mid-jump crossing stored as xD_star",

        "empirical_speed":
            "numpy.gradient(xD_star,tD) within each fixed physical case/Nc group",

        "physical_speed_closure":
            "Xdot_RH = exp(Nc*X)*"
            "[fw(Sw_star)-fw(swc)]/(Sw_star-swc)",

        "interpretation_policy":
            "No numerical acceptance threshold is introduced. "
            "Finite-resolution front extraction and sparse six-snapshot "
            "finite differences can differ from the local analytical RH speed. "
            "Use this audit to quantify that discrepancy before choosing the "
            "runtime Xdot implementation.",

        **front,

        "training_executed":
            False,

        "OOD_used":
            False,

        "TOF_used":
            False,
    }

    FRONT_AUDIT.write_text(
        json.dumps(
            front_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Freeze implementation handoff.
    # -------------------------------------------------------------------------

    handoff = (
        "# V16E-1B2N-XPU — Conservative Residual Implementation Handoff\n\n"
        "## Exact residual to implement\n\n"
        "For network N(xi,tD,X,...), X=xD_star(tD):\n\n"
        "    R_cons = N_tD + Xdot*N_X\n"
        "             - (xi*Xdot/X)*N_xi\n"
        "             + (1/X) d/dxi [ exp(Nc*xi*X) fw(N) ]\n\n"
        "Equivalent expanded form:\n\n"
        "    R_cons = N_tD + Xdot*N_X\n"
        "             + [exp(Nc*xi*X) fw'(N)/X - xi*Xdot/X] N_xi\n"
        "             + Nc exp(Nc*xi*X) fw(N)\n\n"
        "## Front speed\n\n"
        "Physical Rankine-Hugoniot closure:\n\n"
        "    Xdot = exp(Nc*X) sigma_BL\n"
        "    sigma_BL = [fw(Sw_star)-fw(swc)]/(Sw_star-swc)\n\n"
        "The B2N audit quantifies how this closure compares with finite-difference "
        "speeds of the frozen finite-resolution Godunov mid-jump fronts.\n\n"
        "## Critical autograd requirement\n\n"
        "Because tD and xD_star are separate network conditioner entries, "
        "N_tD alone is NOT the physical derivative at fixed xi. The term "
        "Xdot*N_X is mandatory.\n\n"
        "## Next milestone\n\n"
        "Do not train yet. First implement a residual-only verification harness "
        "that compares conservative-form and expanded-form autograd residuals, "
        "checks Nc=0 nesting, checks finite values/bounds, and evaluates the "
        "new residual on the frozen Godunov teacher before any optimizer is created.\n"
    )

    HANDOFF.write_text(
        handoff,
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Final gates.
    # -------------------------------------------------------------------------

    gates.update({
        "derivation_written":
            DERIVATION.exists()
            and DERIVATION.stat().st_size > 0,

        "front_audit_written":
            FRONT_AUDIT.exists()
            and FRONT_AUDIT.stat().st_size > 0,

        "handoff_written":
            HANDOFF.exists()
            and HANDOFF.stat().st_size > 0,

        "front_groups_present":
            front["group_count"] > 0,

        "all_five_Nc_front_audits_present":
            set(front["per_Nc"].keys())
            == {"0.00", "0.05", "0.10", "0.20", "0.30"},

        "front_audit_metrics_finite":
            all(
                finite(rec[k])
                for rec in front["per_Nc"].values()
                for k in (
                    "empirical_speed_mean",
                    "RH_speed_mean",
                    "MAE_speed",
                    "RMSE_speed",
                    "mean_abs_relative_error",
                    "median_abs_relative_error",
                    "p95_abs_relative_error",
                )
            ),

        "network_chain_rule_Xdot_NX_frozen":
            True,

        "moving_grid_term_frozen":
            True,

        "conservative_flux_term_frozen":
            True,

        "new_training_not_authorized":
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

        "no_numeric_threshold":
            True,
    })

    ok = all(
        bool(v)
        for v in gates.values()
    )

    status = (
        "V16E1B2N_XPU_CONSERVATIVE_STAGE2_MOVING_FAN_RESIDUAL_DERIVATION_FROZEN_"
        "EXACT_COORDINATE_CHAIN_RULE_NETWORK_TD_AND_XDSTAR_TOTAL_DERIVATIVE_MOVING_GRID_TERM_"
        "CONSERVATIVE_FLUX_DIVERGENCE_AND_RANKINE_HUGONIOT_FRONT_SPEED_CLOSURE_BOUND_"
        "FROZEN_GODUNOV_FRONT_SPEED_AUDIT_COMPLETE_NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "RESIDUAL_ONLY_AUTOGRAD_VERIFICATION_REQUIRED_BEFORE_NEW_TRAINING_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2N_XPU_DERIVATION_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "derivation_sha256":
            sha256(DERIVATION),

        "front_audit_sha256":
            sha256(FRONT_AUDIT),

        "handoff_sha256":
            sha256(HANDOFF),

        "new_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2O — residual-only autograd verification: implement "
                "the frozen conservative moving-fan residual without training; "
                "cross-check conservative and expanded forms, Nc=0 nesting, "
                "front-speed closure choice, and Godunov-teacher residual behavior"
                if ok else
                "V16E-1B2N-R1 — diagnose failed derivation/audit gate"
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
    print("  Derivation :", sha256(DERIVATION))
    print("  Front audit:", sha256(FRONT_AUDIT))
    print("  Handoff    :", sha256(HANDOFF))
    print("  Summary    :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
