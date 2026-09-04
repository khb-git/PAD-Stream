#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2O-XPU
Conservative Moving-Fan Residual-Only Autograd Verification

Purpose
-------
Implement and verify the V16E-1B2N conservative moving-fan residual WITHOUT
training.

This milestone does four things:

1) Frozen COMP-XPU-004 autograd verification
   Cross-check the conservative-divergence and expanded residual forms.

2) Nc=0 nesting verification
   Verify the corrected residual reduces to the explicit incompressible
   moving-fan conservative form.

3) Front-speed closure audit inside the residual
   Evaluate both:
       Xdot_RH = exp(Nc*X) sigma_BL
   and the finite-difference Xdot extracted from the frozen Godunov front
   trajectories.

4) Model-free Godunov-teacher residual audit
   Use finite differences in the frozen (xi,tD) fan snapshots to evaluate the
   corrected conservative residual directly on the teacher saturation profiles.

NO TRAINING.
NO OPTIMIZER.
NO WEIGHT UPDATE.
NO OOD.
NO TOF.

Important recurrent-model derivative convention
------------------------------------------------
The LSTM maps a sequence to a sequence. For the PDE residual at node j, the
local spatial derivative is the diagonal Jacobian entry

    N_xi(j) = d N_j / d xi_j

rather than d(sum_j N_j)/d xi.

Similarly, tD and X=xD_star are shared conditioner entries. For every output
node j we compute

    N_tD(j) = d N_j / d p11[tD]
    N_X(j)  = d N_j / d p11[xD_star].

This is the direct pointwise derivative convention for the frozen recurrent
parameterization.

Frozen corrected residual
-------------------------
For N=N(xi,tD,X,...), uD=exp(Nc*xi*X),

    R_cons =
        N_tD
        + Xdot*N_X
        - (xi*Xdot/X)*N_xi
        + (1/X) d/dxi [uD*fw(N)]

Expanded:

    R_exp =
        N_tD
        + Xdot*N_X
        + [uD*fw'(N)/X - xi*Xdot/X]*N_xi
        + Nc*uD*fw(N).

At Nc=0:

    R_inc =
        N_tD
        + Xdot*N_X
        + [fw'(N)/X - xi*Xdot/X]*N_xi.

Numerical identity gates use a float32-machine-epsilon-derived bound, not a
scientific model-acceptance threshold.
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
MILESTONE = "V16E-1B2O-XPU"

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

# B2N authority
B2N_SOURCE = (
    R
    / "PAD_Stream_V16E1B2N_XPU_Conservative_Moving_Fan_Residual_Derivation.py"
)
B2N_SOURCE_SHA = "bde47ca9bab21e6156055cf26e50f686f0f417eaeaa42caa7e53d012f79d4bbd"

B2N_DIR = (
    R / "output"
    / "V16_E1B2N_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_DERIVATION"
)
B2N_DERIVATION = B2N_DIR / "V16E1B2N_Conservative_Moving_Fan_Residual_Derivation.json"
B2N_FRONT_AUDIT = B2N_DIR / "V16E1B2N_Godunov_Front_Speed_Closure_Audit.json"
B2N_HANDOFF = B2N_DIR / "V16E1B2N_Residual_Implementation_Handoff.md"
B2N_SUMMARY = B2N_DIR / "PAD_Stream_V16E1B2N_XPU_Summary.json"

B2N_DERIVATION_SHA = "85b6757df96cb256ae4f87d5412f276f92ad8d84600e576b2d34e864b4f35b14"
B2N_FRONT_AUDIT_SHA = "28df3564a306d3e0817490fbfe84ab17dff9b05957b37c5b9afe33f41285f3ea"
B2N_HANDOFF_SHA = "d90ceeffd3e1bb94903bdf86c274c32c604b4fbb76ea7b09b40ea80d2788c73e"
B2N_SUMMARY_SHA = "ca8d9030d1250b277361b462cd5c1a79a4d7c8ccc5c0871dfe869374ee29c0f0"

EXPECTED_B2N_STATUS = (
    "V16E1B2N_XPU_CONSERVATIVE_STAGE2_MOVING_FAN_RESIDUAL_DERIVATION_FROZEN_"
    "EXACT_COORDINATE_CHAIN_RULE_NETWORK_TD_AND_XDSTAR_TOTAL_DERIVATIVE_MOVING_GRID_TERM_"
    "CONSERVATIVE_FLUX_DIVERGENCE_AND_RANKINE_HUGONIOT_FRONT_SPEED_CLOSURE_BOUND_"
    "FROZEN_GODUNOV_FRONT_SPEED_AUDIT_COMPLETE_NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
    "RESIDUAL_ONLY_AUTOGRAD_VERIFICATION_REQUIRED_BEFORE_NEW_TRAINING_B3_NOT_AUTHORIZED"
)

# Direct B2L authority for old teacher characteristic residual comparison.
B2L_DIR = (
    R / "output"
    / "V16_E1B2L_XPU_GODUNOV_TEACHER_CHARACTERISTIC_RESIDUAL_AUDIT"
)
B2L_AUDIT = B2L_DIR / "V16E1B2L_Godunov_Teacher_Characteristic_Residual_Audit.json"
B2L_AUDIT_SHA = "341b7e063fbaa76bac1c59e941765da250a9cc7ee7ff3a3bd6856ca04ffce515"

# Frozen COMP-XPU-004 model
B2J_SOURCE = (
    R
    / "PAD_Stream_V16E1B2J_XPU_COMP_XPU_004_Physics_Aware_Nc_Coordinate_Channel_Reproduction.py"
)
B2J_SOURCE_SHA = "fcc4074863a46f6b8d356a01ff0b4b2182d0ffa3ebc9b3fd053e35282f897a4c"

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

OUT = (
    R / "output"
    / "V16_E1B2O_XPU_CONSERVATIVE_RESIDUAL_AUTOGRAD_VERIFICATION"
)
OUT.mkdir(parents=True, exist_ok=True)

AUTOGRAD_AUDIT = OUT / "V16E1B2O_COMP004_Autograd_Residual_Form_Verification.json"
TEACHER_AUDIT = OUT / "V16E1B2O_Godunov_Teacher_Conservative_Residual_Audit.json"
DECISION = OUT / "V16E1B2O_Residual_Implementation_Decision.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2O_XPU_Summary.json"

NC_VALUES = [0.0, 0.05, 0.10, 0.20, 0.30]
SEED = 1337
AUTOGRAD_PROFILES_PER_NC = 2

# Machine-precision-derived implementation identity multiplier.
FLOAT32_EPS = float(np.finfo(np.float32).eps)
IDENTITY_EPS_MULTIPLIER = 512.0


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
    # p11 = [no,nw,swi,sor,mu_w,mu_o,phi,tD,X,Sw_star,Nc]
    return tuple(float(row[i]) for i in [0, 1, 2, 3, 4, 5, 6, 10])


def split_indices(n: int):
    rng = np.random.default_rng(SEED)
    idx = np.arange(n)
    rng.shuffle(idx)
    n_train = int(0.8 * n)
    return idx[:n_train], idx[n_train:]


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


def rh_speed_np(M, row: np.ndarray):
    p = make_p_from_row(M, row)
    swc = float(row[2])
    X = float(row[8])
    Sw_star = float(row[9])
    Nc = float(row[10])

    fw_pair = M.fractional_flow_np(
        np.asarray([swc, Sw_star], dtype=float),
        p,
    )
    fw_r = float(fw_pair[0])
    fw_l = float(fw_pair[1])

    sigma = (fw_l - fw_r) / max(Sw_star - swc, 1e-30)
    return float(np.exp(Nc * X) * sigma), float(sigma)


def build_fd_speed_array(p11: np.ndarray):
    groups = {}
    for i, row in enumerate(p11):
        groups.setdefault(group_key(row), []).append(i)

    speed = np.full(len(p11), np.nan, dtype=np.float64)

    for ids in groups.values():
        ids = np.asarray(ids, dtype=int)
        rows = p11[ids]
        order = np.argsort(rows[:, 7])
        ids_sorted = ids[order]
        tD = p11[ids_sorted, 7].astype(float)
        X = p11[ids_sorted, 8].astype(float)

        if len(ids_sorted) < 3 or not np.all(np.diff(tD) > 0.0):
            continue

        dX = np.gradient(
            X,
            tD,
            edge_order=2 if len(X) >= 3 else 1,
        )
        speed[ids_sorted] = dX

    return speed


def select_autograd_profiles(p11: np.ndarray, holdout_idx: np.ndarray):
    selected = []

    for nc in NC_VALUES:
        ids = holdout_idx[
            np.isclose(
                p11[holdout_idx, 10],
                nc,
                atol=1e-7,
            )
        ]

        # Stable deterministic pick: earliest tD profiles.
        ids = ids[np.argsort(p11[ids, 7])]
        if len(ids) < AUTOGRAD_PROFILES_PER_NC:
            raise RuntimeError(
                f"Not enough holdout profiles for Nc={nc}"
            )
        selected.extend(
            ids[:AUTOGRAD_PROFILES_PER_NC].tolist()
        )

    return np.asarray(selected, dtype=int)


def machine_identity_bound(a: torch.Tensor, b: torch.Tensor) -> float:
    scale = max(
        1.0,
        float(torch.max(torch.abs(a)).detach().cpu()),
        float(torch.max(torch.abs(b)).detach().cpu()),
    )
    # Error budget scales only with float32 epsilon and expression magnitude.
    return IDENTITY_EPS_MULTIPLIER * FLOAT32_EPS * scale


# =============================================================================
# Pointwise recurrent autograd
# =============================================================================

def diagonal_output_derivatives(
    model,
    xi: torch.Tensor,
    p11: torch.Tensor,
    S: torch.Tensor,
):
    """
    Return pointwise diagonal/local derivatives:
      N_xi[j] = dN_j/dxi_j
      N_tD[j] = dN_j/dp11_tD
      N_X[j] = dN_j/dp11_X

    xi and p11 must be leaf tensors with requires_grad=True.
    """
    B, T, _ = S.shape

    N_xi = torch.empty_like(S)
    N_tD = torch.empty_like(S)
    N_X = torch.empty_like(S)

    for j in range(T):
        gx, gp = torch.autograd.grad(
            outputs=S[:, j, :].sum(),
            inputs=(xi, p11),
            retain_graph=True,
            create_graph=False,
            allow_unused=False,
        )

        N_xi[:, j, 0] = gx[:, j, 0]
        N_tD[:, j, 0] = gp[:, 7]
        N_X[:, j, 0] = gp[:, 8]

    return N_xi, N_tD, N_X


def diagonal_flux_derivative(
    xi: torch.Tensor,
    flux: torch.Tensor,
):
    B, T, _ = flux.shape
    F_xi = torch.empty_like(flux)

    for j in range(T):
        gx = torch.autograd.grad(
            outputs=flux[:, j, :].sum(),
            inputs=xi,
            retain_graph=True,
            create_graph=False,
            allow_unused=False,
        )[0]

        F_xi[:, j, 0] = gx[:, j, 0]

    return F_xi


def comp004_residual_forms(
    M,
    model,
    xi_np: np.ndarray,
    p11_np: np.ndarray,
    xdot_np: np.ndarray,
    device,
):
    xi = (
        torch.from_numpy(xi_np)
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )
    p11 = (
        torch.from_numpy(p11_np)
        .to(device)
        .detach()
        .clone()
        .requires_grad_(True)
    )

    xdot = torch.from_numpy(
        np.asarray(xdot_np, dtype=np.float32)
    ).to(device).reshape(-1, 1, 1)

    S = model(xi, p11)

    N_xi, N_tD, N_X = diagonal_output_derivatives(
        model,
        xi,
        p11,
        S,
    )

    fw = M.fractional_flow_torch(
        S,
        p11,
    )

    # fw is pointwise in S, so this produces fw'(S) nodewise.
    dfdS = torch.autograd.grad(
        outputs=fw,
        inputs=S,
        grad_outputs=torch.ones_like(fw),
        retain_graph=True,
        create_graph=False,
        only_inputs=True,
    )[0]

    X = p11[:, 8:9].unsqueeze(1)
    Nc = p11[:, 10:11].unsqueeze(1)

    uD = torch.exp(
        Nc * xi * X
    )

    flux = uD * fw

    F_xi = diagonal_flux_derivative(
        xi,
        flux,
    )

    R_cons = (
        N_tD
        + xdot * N_X
        - (xi * xdot / X) * N_xi
        + F_xi / X
    )

    R_exp = (
        N_tD
        + xdot * N_X
        + (
            uD * dfdS / X
            - xi * xdot / X
        ) * N_xi
        + Nc * uD * fw
    )

    # Explicit Nc=0 moving-fan incompressible residual.
    R_inc = (
        N_tD
        + xdot * N_X
        + (
            dfdS / X
            - xi * xdot / X
        ) * N_xi
    )

    # Interior fan nodes only.
    sl = slice(1, -1)

    out = {
        "S": S[:, sl, :].detach(),
        "N_xi": N_xi[:, sl, :].detach(),
        "N_tD": N_tD[:, sl, :].detach(),
        "N_X": N_X[:, sl, :].detach(),
        "fw": fw[:, sl, :].detach(),
        "dfdS": dfdS[:, sl, :].detach(),
        "uD": uD[:, sl, :].detach(),
        "R_cons": R_cons[:, sl, :].detach(),
        "R_exp": R_exp[:, sl, :].detach(),
        "R_inc": R_inc[:, sl, :].detach(),
        "Nc": Nc.detach(),
        "X": X.detach(),
        "xdot": xdot.detach(),
    }

    return out


def summarize_form_verification(forms):
    R1 = forms["R_cons"]
    R2 = forms["R_exp"]

    diff = R1 - R2
    max_diff = float(
        torch.max(torch.abs(diff)).cpu()
    )
    rms_diff = float(
        torch.sqrt(torch.mean(diff ** 2)).cpu()
    )
    bound = machine_identity_bound(
        R1,
        R2,
    )

    result = {
        "conservative_form_MSE":
            float(torch.mean(R1 ** 2).cpu()),
        "expanded_form_MSE":
            float(torch.mean(R2 ** 2).cpu()),
        "max_abs_form_difference":
            max_diff,
        "rms_form_difference":
            rms_diff,
        "machine_epsilon_identity_bound":
            bound,
        "forms_match_within_machine_epsilon_scaled_bound":
            bool(max_diff <= bound),
    }

    # Nc=0 rows.
    nc_mask = (
        torch.abs(forms["Nc"].reshape(-1))
        < 1e-8
    )
    if torch.any(nc_mask):
        re = R2[nc_mask]
        ri = forms["R_inc"][nc_mask]
        d = re - ri

        nest_max = float(
            torch.max(torch.abs(d)).cpu()
        )
        nest_rms = float(
            torch.sqrt(torch.mean(d ** 2)).cpu()
        )
        nest_bound = machine_identity_bound(
            re,
            ri,
        )

        result.update({
            "Nc0_expanded_vs_explicit_incompressible_max_abs_difference":
                nest_max,
            "Nc0_expanded_vs_explicit_incompressible_rms_difference":
                nest_rms,
            "Nc0_machine_epsilon_identity_bound":
                nest_bound,
            "Nc0_nesting_matches_within_machine_epsilon_scaled_bound":
                bool(nest_max <= nest_bound),
        })
    else:
        result.update({
            "Nc0_expanded_vs_explicit_incompressible_max_abs_difference":
                None,
            "Nc0_expanded_vs_explicit_incompressible_rms_difference":
                None,
            "Nc0_machine_epsilon_identity_bound":
                None,
            "Nc0_nesting_matches_within_machine_epsilon_scaled_bound":
                False,
        })

    return result


# =============================================================================
# Godunov-teacher finite-difference residual
# =============================================================================

def teacher_residual_audit(M, xi_all, Sw_all, p11_all, holdout_idx):
    groups = {}
    for i, row in enumerate(p11_all):
        groups.setdefault(group_key(row), []).append(i)

    is_holdout = np.zeros(len(p11_all), dtype=bool)
    is_holdout[holdout_idx] = True

    collectors = {
        f"{nc:.2f}": {
            "RH_all": [],
            "FD_all": [],
            "RH_holdout": [],
            "FD_holdout": [],
        }
        for nc in NC_VALUES
    }

    invalid_groups = 0

    for ids in groups.values():
        ids = np.asarray(ids, dtype=int)
        rows = p11_all[ids]
        order = np.argsort(rows[:, 7])
        ids = ids[order]
        rows = p11_all[ids]

        tD = rows[:, 7].astype(float)
        X = rows[:, 8].astype(float)
        Nc = float(rows[0, 10])

        if len(ids) < 3 or not np.all(np.diff(tD) > 0.0):
            invalid_groups += 1
            continue

        xi_mat = xi_all[ids, :, 0].astype(float)
        S_mat = Sw_all[ids, :, 0].astype(float)

        # Frozen fan resampling uses common uniform xi.
        xi_ref = xi_mat[0]
        if not np.allclose(
            xi_mat,
            xi_ref[None, :],
            rtol=0.0,
            atol=1e-7,
        ):
            invalid_groups += 1
            continue

        # Derivatives in moving coordinates.
        S_t = np.gradient(
            S_mat,
            tD,
            axis=0,
            edge_order=2,
        )
        S_xi = np.gradient(
            S_mat,
            xi_ref,
            axis=1,
            edge_order=2,
        )

        p = make_p_from_row(
            M,
            rows[0],
        )
        fw = M.fractional_flow_np(
            S_mat,
            p,
        )

        uD = np.exp(
            Nc * xi_ref[None, :] * X[:, None]
        )
        flux = uD * fw
        F_xi = np.gradient(
            flux,
            xi_ref,
            axis=1,
            edge_order=2,
        )

        Xdot_fd = np.gradient(
            X,
            tD,
            edge_order=2,
        )

        # Vector RH speed evaluated at each snapshot.
        swc = float(rows[0, 2])
        Sw_star = float(rows[0, 9])

        fw_pair = M.fractional_flow_np(
            np.asarray([swc, Sw_star]),
            p,
        )
        sigma = (
            float(fw_pair[1] - fw_pair[0])
            / max(Sw_star - swc, 1e-30)
        )
        Xdot_rh = np.exp(Nc * X) * sigma

        R_fd = (
            S_t
            - (
                xi_ref[None, :]
                * Xdot_fd[:, None]
                / X[:, None]
            ) * S_xi
            + F_xi / X[:, None]
        )

        R_rh = (
            S_t
            - (
                xi_ref[None, :]
                * Xdot_rh[:, None]
                / X[:, None]
            ) * S_xi
            + F_xi / X[:, None]
        )

        # Same interior-node convention as prior Stage-2 physics residual.
        R_fd = R_fd[:, 1:-1]
        R_rh = R_rh[:, 1:-1]

        key = f"{Nc:.2f}"

        collectors[key]["FD_all"].extend(
            R_fd.reshape(-1).tolist()
        )
        collectors[key]["RH_all"].extend(
            R_rh.reshape(-1).tolist()
        )

        hold_rows = is_holdout[ids]
        if np.any(hold_rows):
            collectors[key]["FD_holdout"].extend(
                R_fd[hold_rows].reshape(-1).tolist()
            )
            collectors[key]["RH_holdout"].extend(
                R_rh[hold_rows].reshape(-1).tolist()
            )

    out = {}

    for nc, rec in collectors.items():
        out[nc] = {}

        for label, values in rec.items():
            arr = np.asarray(
                values,
                dtype=float,
            )
            if arr.size == 0:
                raise RuntimeError(
                    f"No teacher residual values for {nc} {label}"
                )

            out[nc][label] = {
                "n_scalar_residuals":
                    int(arr.size),
                "MSE":
                    float(np.mean(arr ** 2)),
                "RMSE":
                    float(np.sqrt(np.mean(arr ** 2))),
                "MAE":
                    float(np.mean(np.abs(arr))),
                "max_abs":
                    float(np.max(np.abs(arr))),
            }

    return {
        "groups":
            int(len(groups)),
        "invalid_groups":
            int(invalid_groups),
        "per_Nc":
            out,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 80)
    print("PAD-Stream V16E-1B2O-XPU")
    print("Conservative Moving-Fan Residual-Only Autograd Verification")
    print("=" * 80)
    print("NO TRAINING — NO OPTIMIZER — verification only.\n")

    if SUMMARY.exists():
        raise RuntimeError(
            "V16E-1B2O summary already exists; refusing overwrite."
        )

    gates = {
        "Stage2_source_SHA_exact":
            exact(STAGE2, STAGE2_SHA),
        "base_runner_SHA_exact":
            exact(BASE_RUNNER, BASE_RUNNER_SHA),
        "dataset_SHA_exact":
            exact(DATASET, DATASET_SHA),

        "B2N_source_SHA_exact":
            exact(B2N_SOURCE, B2N_SOURCE_SHA),
        "B2N_derivation_SHA_exact":
            exact(B2N_DERIVATION, B2N_DERIVATION_SHA),
        "B2N_front_audit_SHA_exact":
            exact(B2N_FRONT_AUDIT, B2N_FRONT_AUDIT_SHA),
        "B2N_handoff_SHA_exact":
            exact(B2N_HANDOFF, B2N_HANDOFF_SHA),
        "B2N_summary_SHA_exact":
            exact(B2N_SUMMARY, B2N_SUMMARY_SHA),

        "B2L_audit_SHA_exact":
            exact(B2L_AUDIT, B2L_AUDIT_SHA),

        "B2J_source_SHA_exact":
            exact(B2J_SOURCE, B2J_SOURCE_SHA),
        "COMP004_checkpoint_SHA_exact":
            exact(COMP004_CHECKPOINT, COMP004_CHECKPOINT_SHA),
        "COMP004_manifest_SHA_exact":
            exact(COMP004_MANIFEST, COMP004_MANIFEST_SHA),
        "COMP004_summary_SHA_exact":
            exact(COMP004_SUMMARY, COMP004_SUMMARY_SHA),
    }

    b2n = read_json(B2N_SUMMARY) if B2N_SUMMARY.exists() else {}

    gates.update({
        "B2N_status_exact":
            b2n.get("status") == EXPECTED_B2N_STATUS,
        "B2N_new_training_false":
            b2n.get("new_training_authorized") is False,
        "B2N_B3_false":
            b2n.get("B3_authorized") is False,
    })

    print("AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "B2O blocked by authority mismatch."
        )

    M = import_module(
        BASE_RUNNER,
        "v16e1b2c_base",
    )
    J = import_module(
        B2J_SOURCE,
        "v16e1b2j_comp004",
    )

    if not torch.xpu.is_available():
        raise RuntimeError(
            "Intel XPU unavailable for B2O autograd verification."
        )

    device = torch.device("xpu")

    EtaModel = J.build_eta_model_class(M)
    payload = torch.load(
        COMP004_CHECKPOINT,
        map_location="cpu",
        weights_only=False,
    )

    model = EtaModel()
    model.load_state_dict(
        payload["model_state_dict"],
        strict=True,
    )
    model.to(device)
    model.eval()

    gates.update({
        "COMP004_model_eval_mode":
            model.training is False,
        "COMP004_checkpoint_unchanged":
            sha256(COMP004_CHECKPOINT)
            == COMP004_CHECKPOINT_SHA,
        "COMP004_eta_channel_exact":
            payload.get("sequence_features")
            == ["xi", "eta"],
        "COMP004_raw_p11_unscaled":
            payload.get("raw_p11_scaled")
            is False,
        "COMP004_physical_Nc_unchanged":
            payload.get("physical_Nc_unchanged")
            is True,
    })

    d = np.load(DATASET)
    xi_all = d["xi"]
    Sw_all = d["Sw"]
    p11_all = d["p11"]

    _, holdout_idx = split_indices(
        len(xi_all)
    )

    xdot_fd_all = build_fd_speed_array(
        p11_all
    )

    selected = select_autograd_profiles(
        p11_all,
        holdout_idx,
    )

    if not np.isfinite(
        xdot_fd_all[selected]
    ).all():
        raise RuntimeError(
            "Selected profiles have missing FD front speed."
        )

    xdot_rh = np.asarray([
        rh_speed_np(
            M,
            p11_all[i],
        )[0]
        for i in selected
    ], dtype=np.float32)

    xdot_fd = xdot_fd_all[
        selected
    ].astype(np.float32)

    xi_sel = xi_all[
        selected
    ].astype(np.float32)

    p11_sel = p11_all[
        selected
    ].astype(np.float32)

    print("\nAUTOGRAD RESIDUAL FORM CROSS-CHECK — RH XD0T")
    forms_rh = comp004_residual_forms(
        M,
        model,
        xi_sel,
        p11_sel,
        xdot_rh,
        device,
    )
    verify_rh = summarize_form_verification(
        forms_rh
    )

    print(
        "  conservative MSE :",
        f"{verify_rh['conservative_form_MSE']:.6e}"
    )
    print(
        "  expanded MSE     :",
        f"{verify_rh['expanded_form_MSE']:.6e}"
    )
    print(
        "  max |form diff|  :",
        f"{verify_rh['max_abs_form_difference']:.6e}"
    )
    print(
        "  eps-derived bound:",
        f"{verify_rh['machine_epsilon_identity_bound']:.6e}"
    )
    print(
        "  form identity     :",
        "PASS"
        if verify_rh[
            "forms_match_within_machine_epsilon_scaled_bound"
        ]
        else "FAIL"
    )
    print(
        "  Nc=0 nesting      :",
        "PASS"
        if verify_rh[
            "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
        ]
        else "FAIL"
    )

    print("\nAUTOGRAD RESIDUAL FORM CROSS-CHECK — FD XD0T")
    forms_fd = comp004_residual_forms(
        M,
        model,
        xi_sel,
        p11_sel,
        xdot_fd,
        device,
    )
    verify_fd = summarize_form_verification(
        forms_fd
    )

    print(
        "  conservative MSE :",
        f"{verify_fd['conservative_form_MSE']:.6e}"
    )
    print(
        "  expanded MSE     :",
        f"{verify_fd['expanded_form_MSE']:.6e}"
    )
    print(
        "  max |form diff|  :",
        f"{verify_fd['max_abs_form_difference']:.6e}"
    )
    print(
        "  eps-derived bound:",
        f"{verify_fd['machine_epsilon_identity_bound']:.6e}"
    )
    print(
        "  form identity     :",
        "PASS"
        if verify_fd[
            "forms_match_within_machine_epsilon_scaled_bound"
        ]
        else "FAIL"
    )
    print(
        "  Nc=0 nesting      :",
        "PASS"
        if verify_fd[
            "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
        ]
        else "FAIL"
    )

    autograd_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "NO_TRAINING_COMP004_CONSERVATIVE_RESIDUAL_AUTOGRAD_FORM_VERIFICATION",

        "selected_profile_count":
            int(len(selected)),

        "selected_profiles_per_Nc":
            AUTOGRAD_PROFILES_PER_NC,

        "selected_dataset_indices":
            [int(x) for x in selected],

        "derivative_convention":
            {
                "N_xi":
                    "diagonal Jacobian dN_j/dxi_j",
                "N_tD":
                    "dN_j/dp11[tD] for each output node j",
                "N_X":
                    "dN_j/dp11[xD_star] for each output node j",
            },

        "front_speed_closures": {
            "Rankine_Hugoniot":
                verify_rh,
            "finite_difference_Godunov_front":
                verify_fd,
        },

        "identity_bound_policy":
            {
                "float32_epsilon":
                    FLOAT32_EPS,
                "multiplier":
                    IDENTITY_EPS_MULTIPLIER,
                "formula":
                    "multiplier * float32_epsilon * max(1, |form scales|)",
                "classification":
                    "computational algebraic-identity tolerance; not a scientific acceptance threshold",
            },

        "no_training":
            True,
        "no_optimizer":
            True,
        "no_weight_update":
            True,
    }

    AUTOGRAD_AUDIT.write_text(
        json.dumps(
            autograd_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Model-free teacher audit.
    # -------------------------------------------------------------------------

    print("\nGODUNOV TEACHER — CORRECTED CONSERVATIVE MOVING-FAN RESIDUAL")

    teacher = teacher_residual_audit(
        M,
        xi_all,
        Sw_all,
        p11_all,
        holdout_idx,
    )

    old_char = read_json(
        B2L_AUDIT
    )[
        "teacher_characteristic_physics_loss"
    ][
        "holdout"
    ]

    comparison = {}

    for nc in [f"{x:.2f}" for x in NC_VALUES]:
        rh = teacher["per_Nc"][nc]["RH_holdout"]
        fd = teacher["per_Nc"][nc]["FD_holdout"]
        old = float(
            old_char[nc][
                "teacher_characteristic_physics_mse"
            ]
        )

        comparison[nc] = {
            "old_characteristic_teacher_MSE":
                old,
            "corrected_conservative_RH_teacher_MSE":
                float(rh["MSE"]),
            "corrected_conservative_FD_teacher_MSE":
                float(fd["MSE"]),
            "old_over_corrected_RH_MSE_ratio":
                float(
                    old
                    / max(float(rh["MSE"]), 1e-30)
                ),
            "old_over_corrected_FD_MSE_ratio":
                float(
                    old
                    / max(float(fd["MSE"]), 1e-30)
                ),
        }

        print(
            f"  Nc={nc} "
            f"| old-char={old:.6e} "
            f"| corrected-RH={rh['MSE']:.6e} "
            f"| corrected-FD={fd['MSE']:.6e}"
        )

    teacher_payload = {
        "milestone":
            MILESTONE,

        "classification":
            "MODEL_FREE_GODUNOV_TEACHER_CORRECTED_CONSERVATIVE_RESIDUAL_AUDIT",

        "teacher_derivatives":
            {
                "S_tD_at_fixed_xi":
                    "finite difference across six frozen fan snapshots within each physical case/Nc group",
                "S_xi":
                    "finite difference along common frozen xi fan grid",
                "flux_xi":
                    "finite difference of exp(Nc*xi*X)*fw(S) along xi",
            },

        "front_speed_closures":
            {
                "RH":
                    "exp(Nc*X)*sigma_BL",
                "FD":
                    "finite difference dX/dtD of frozen Godunov mid-jump front",
            },

        "residual_nodes":
            "interior fan nodes only (1:-1)",

        "corrected_residual":
            teacher,

        "comparison_to_B2L_old_characteristic_teacher_residual":
            comparison,

        "evaluation_semantics":
            "diagnostic only; holdout labels are not independent/OOD because finite-difference temporal derivatives use complete within-case trajectories",

        "no_training":
            True,
        "no_OOD":
            True,
        "no_TOF":
            True,
    }

    TEACHER_AUDIT.write_text(
        json.dumps(
            teacher_payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Decision artifact: implementation verification only, not training auth.
    # -------------------------------------------------------------------------

    gates.update({
        "RH_forms_match_machine_identity_bound":
            verify_rh[
                "forms_match_within_machine_epsilon_scaled_bound"
            ],

        "FD_forms_match_machine_identity_bound":
            verify_fd[
                "forms_match_within_machine_epsilon_scaled_bound"
            ],

        "RH_Nc0_nesting_matches_machine_identity_bound":
            verify_rh[
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ],

        "FD_Nc0_nesting_matches_machine_identity_bound":
            verify_fd[
                "Nc0_nesting_matches_within_machine_epsilon_scaled_bound"
            ],

        "teacher_all_Nc_present":
            set(
                teacher[
                    "per_Nc"
                ].keys()
            )
            == {
                "0.00", "0.05", "0.10", "0.20", "0.30"
            },

        "teacher_corrected_metrics_finite":
            all(
                finite(rec[closure][metric])
                for rec in teacher["per_Nc"].values()
                for closure in (
                    "RH_all",
                    "FD_all",
                    "RH_holdout",
                    "FD_holdout",
                )
                for metric in (
                    "MSE",
                    "RMSE",
                    "MAE",
                    "max_abs",
                )
            ),

        "COMP004_checkpoint_still_unchanged":
            sha256(COMP004_CHECKPOINT)
            == COMP004_CHECKPOINT_SHA,

        "autograd_audit_written":
            AUTOGRAD_AUDIT.exists()
            and AUTOGRAD_AUDIT.stat().st_size > 0,

        "teacher_audit_written":
            TEACHER_AUDIT.exists()
            and TEACHER_AUDIT.stat().st_size > 0,

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

        "implementation_result":
            (
                "CONSERVATIVE_AND_EXPANDED_AUTOGRAD_FORMS_IMPLEMENTED_AND_"
                "MACHINE_PRECISION_CROSSCHECKED_WITH_NC0_NESTING"
                if (
                    gates["RH_forms_match_machine_identity_bound"]
                    and gates["FD_forms_match_machine_identity_bound"]
                    and gates["RH_Nc0_nesting_matches_machine_identity_bound"]
                    and gates["FD_Nc0_nesting_matches_machine_identity_bound"]
                )
                else
                "AUTOGRAD_FORM_OR_NC0_IDENTITY_CROSSCHECK_REQUIRES_REPAIR"
            ),

        "front_speed_result":
            {
                "RH":
                    {
                        "COMP004_residual_MSE":
                            verify_rh[
                                "conservative_form_MSE"
                            ],
                    },
                "FD":
                    {
                        "COMP004_residual_MSE":
                            verify_fd[
                                "conservative_form_MSE"
                            ],
                    },
                "teacher_per_Nc":
                    {
                        nc: {
                            "RH_holdout_MSE":
                                rec["RH_holdout"]["MSE"],
                            "FD_holdout_MSE":
                                rec["FD_holdout"]["MSE"],
                        }
                        for nc, rec
                        in teacher["per_Nc"].items()
                    },
            },

        "training_authorized":
            False,

        "B3_authorized":
            False,

        "next_decision_required":
            "Interpret corrected teacher residual behavior and RH-vs-FD closure "
            "before freezing a corrected Stage-2 training protocol.",

        "prohibited":
            [
                "creating an optimizer in B2O",
                "modifying COMP-XPU-004",
                "using old characteristic residual as the corrected conservative residual",
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
        for v in gates.values()
    )

    status = (
        "V16E1B2O_XPU_CONSERVATIVE_MOVING_FAN_RESIDUAL_AUTOGRAD_VERIFICATION_COMPLETE_"
        "COMP_XPU_004_LOCAL_DIAGONAL_JACOBIANS_TD_XDSTAR_CHAIN_RULE_CONSERVATIVE_AND_EXPANDED_FORMS_"
        "MACHINE_PRECISION_CROSSCHECKED_NC0_MOVING_FAN_NESTING_VERIFIED_RH_AND_FD_FRONT_SPEED_CLOSURES_EVALUATED_"
        "GODUNOV_TEACHER_CORRECTED_CONSERVATIVE_RESIDUAL_AUDIT_COMPLETE_NO_TRAINING_NO_WEIGHT_CHANGE_NO_OOD_NO_TOF_"
        "CORRECTED_STAGE2_TRAINING_PROTOCOL_REQUIRES_INTERPRETATION_B3_NOT_AUTHORIZED"
        if ok else
        "V16E1B2O_XPU_RESIDUAL_VERIFICATION_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone":
            MILESTONE,

        "status":
            status,

        "autograd_audit_sha256":
            sha256(AUTOGRAD_AUDIT),

        "teacher_audit_sha256":
            sha256(TEACHER_AUDIT),

        "decision_sha256":
            sha256(DECISION),

        "new_training_authorized":
            False,

        "B3_authorized":
            False,

        "next_milestone":
            (
                "V16E-1B2P — interpret B2O corrected teacher residual and "
                "RH-vs-FD closure; if coherent, freeze the corrected conservative "
                "Stage-2 training protocol before any optimizer is created"
                if ok else
                "V16E-1B2O-R1 — diagnose residual implementation/audit gate failure"
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
    print(" ", status)

    print("\nHASHES")
    print("  Autograd audit:", sha256(AUTOGRAD_AUDIT))
    print("  Teacher audit :", sha256(TEACHER_AUDIT))
    print("  Decision      :", sha256(DECISION))
    print("  Summary       :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
