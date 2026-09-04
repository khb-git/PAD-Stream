#!/usr/bin/env python3
"""
PAD-Stream V16E-1B1-XPU
Final Incompressible BL PI-RNN Native-Coordinate Reproduction
PyTorch / Intel XPU framework-equivalent acceleration branch

Experiment ID
-------------
V16E-BLREP-INC-XPU-001

Purpose
-------
Accelerate the final incompressible Buckley-Leverett PI-RNN reproduction on an
Intel Arc XPU while preserving the frozen scientific model definition:

  * same analytical BL / Welge teacher,
  * same 10 conditioning variables,
  * same xi = xD/xD_star native coordinate,
  * same two stacked LSTM(64) topology,
  * same sigmoid saturation range map,
  * same loss terms and weights,
  * same Adam learning rate,
  * same logical batch size = 8192,
  * same 400 epochs,
  * same seed = 1337,
  * same source-native 80/20 reproduction holdout semantics.

This is a FRAMEWORK-EQUIVALENT PORT, not a bitwise TensorFlow reproduction.
PyTorch and Keras have different kernels and runtime numerics. The framework
change is explicit and receives a new experiment identity.

Important
---------
* NO TOF transformation.
* NO OOD claim.
* NO mixed precision.
* NO PhysicsNeMo.
* EXP-CS1 remains closed.
* geology0029 remains consumed.
* Historical TensorFlow checkpoints remain unavailable.
* Any output from this script is a NEW V16E XPU reproduction artifact.

The exact analytical physics and dataset-generation equations below are ported
from the frozen final source:

  pi_rnn_stage1_incompressible.py
  SHA-256:
  98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58
"""

from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import itertools
import json
import math
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn


# =============================================================================
# Paths and immutable authorities
# =============================================================================

R = Path(__file__).resolve().parent

EXPERIMENT_ID = "V16E-BLREP-INC-XPU-001"

OUT = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

DATASET_DIR = R / "output" / "V16_E1B_XPU_DATASETS"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

DATASET = DATASET_DIR / "V16E_STAGE1_ANALYTICAL_FAN_DATASET_SEED1337.npz"
DATASET_META = DATASET_DIR / "V16E_STAGE1_ANALYTICAL_FAN_DATASET_SEED1337.json"

CHECKPOINT = OUT / "V16E_BLREP_INC_XPU_001.pt"
CONFIG = OUT / "V16E_BLREP_INC_XPU_001_Config.json"
PORT_PROTOCOL = OUT / "V16E_BLREP_INC_XPU_001_Framework_Port_Protocol.json"
MANIFEST = OUT / "V16E_BLREP_INC_XPU_001_Manifest.json"
METRICS = OUT / "V16E_BLREP_INC_XPU_001_Metrics.json"
HISTORY = OUT / "V16E_BLREP_INC_XPU_001_Training_History.json"
SUMMARY = OUT / "PAD_Stream_V16E1B1_XPU_Summary.json"

# Standard TensorFlow E1B1 summary: if this exists, the CPU experiment completed.
TF_E1B1_SUMMARY = (
    R / "output"
    / "V16_E1B_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-INC-001"
    / "PAD_Stream_V16E1B1_Summary.json"
)

# Frozen V16E-1A
E1A_SOURCE = R / "PAD_Stream_V16E1A_BL_Native_Coordinate_Reproduction_Protocol_Freeze.py"
E1A_SOURCE_SHA = "136306c90e22feda82f4bd2ae32ba0417e3753668331ddc395402e0cdd92623d"

E1A_DIR = R / "output" / "V16_E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FREEZE"
E1A_PROTOCOL = E1A_DIR / "V16E1A_BL_Native_Coordinate_Reproduction_Protocol.json"
E1A_ISSUES = E1A_DIR / "V16E1A_Known_Source_Metadata_Issues.json"
E1A_ARTIFACTS = E1A_DIR / "V16E1A_Reproduction_Artifact_and_Experiment_Contract.json"
E1A_HANDOFF = E1A_DIR / "V16E1A_Execution_Handoff.md"
E1A_SUMMARY = E1A_DIR / "PAD_Stream_V16E1A_Summary.json"

E1A_PROTOCOL_SHA = "207045957d9a88589abd41b30f963adc061a48ad51e4f55402721bd0e99bdfab"
E1A_ISSUES_SHA = "45513abf482aba34ca113ffd84192f8c32b46b2a3ed0da863c524fce7944f54c"
E1A_ARTIFACTS_SHA = "cffd11401b477be3e69fe1f733bf3f9eabd86a369207af42f06b2b0b5a6efa43"
E1A_HANDOFF_SHA = "65dc4fa429daa02b5c22d6e10ac34cb168a6143d662ba39eaffcac6cc67c6c65"
E1A_SUMMARY_SHA = "e2c682f98c2f27316043695fcb71084e9c3130ba6fd77a44e9891fb70ecd059a"

EXPECTED_E1A_STATUS = (
    "V16E1A_BL_NATIVE_COORDINATE_REPRODUCTION_PROTOCOL_FROZEN_"
    "FOUR_FINAL_BL_PHASES_BOUND_"
    "STAGE3_13D_STAGE4_14D_EXECUTABLE_INTERFACES_RECONCILED_"
    "SOURCE_NATIVE_HOLDOUT_SEMANTICS_FROZEN_NO_OOD_CLAIM_"
    "NEW_V16E_REPRODUCTION_ARTIFACT_CONTRACT_FROZEN_"
    "V16E1B1_INCOMPRESSIBLE_REPRODUCTION_AUTHORIZED"
)

SOURCE = R / "pi_rnn_stage1_incompressible.py"
SOURCE_SHA = "98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58"


# =============================================================================
# Frozen Stage-1 constants / configuration
# =============================================================================

FT3_PER_BBL = 5.615
EPS = 1e-12

SEED = 1337
EPOCHS = 400
LR = 1e-3
LOGICAL_BATCH = 8192

HIDDEN = 64
LAYERS = 2
PARAM_DIM = 10

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 0.05
LAMBDA_BC = 5.0
LAMBDA_TIP = 5.0
LAMBDA_ANCHOR = 10.0
LAMBDA_MONO = 0.2
LAMBDA_SHAPE = 0.0

CONDITIONING = [
    "no", "nw", "swi", "sor",
    "mu_w", "mu_o", "phi",
    "tD", "xD_star", "Sw_star",
]

BASE_P = {
    "nw": 2.0,
    "no": 2.0,
    "mu_w": 0.5,
    "mu_o": 5.0,
    "swc": 0.20,
    "sor": 0.20,
    "krw_max": 0.8,
    "kro_max": 0.8,
    "bw": 1.02,
    "bo": 1.25,
    "phi": 0.20,
    "A": 160_000.0,
    "x_ip": 2_000.0,
    "i_w": 1_000.0,
    "injector_at_left": True,
}


# =============================================================================
# General helpers
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


def jsonable(v):
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.floating, np.integer, np.bool_)):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def finite_number(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def sync_xpu():
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        torch.xpu.synchronize()


# =============================================================================
# Exact Stage-1 analytical physics port
# =============================================================================

REQUIRED_KEYS = (
    "nw", "no", "mu_w", "mu_o", "swc", "sor", "krw_max", "kro_max",
    "phi", "A", "x_ip", "i_w",
)


def validate_params(p: dict) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in p]
    if missing:
        raise KeyError(f"Missing required parameter(s): {missing}")
    assert 0.0 <= p["swc"] < 1.0
    assert 0.0 <= p["sor"] < 1.0
    assert (p["swc"] + p["sor"]) < 1.0
    assert (1.0 - p["swc"] - p["sor"]) > EPS
    assert p["mu_w"] > 0.0 and p["mu_o"] > 0.0
    assert p["nw"] > 0.0 and p["no"] > 0.0
    assert 0.0 < p["krw_max"] <= 1.0 and 0.0 < p["kro_max"] <= 1.0
    assert 0.0 < p["phi"] < 1.0
    for k in ("A", "x_ip", "i_w"):
        assert p[k] > 0.0


def calculate_relative_permeability_np(
    sw_local: np.ndarray,
    so_local: np.ndarray,
    p: dict,
):
    swc, sor = p["swc"], p["sor"]
    nw, no = p["nw"], p["no"]
    krw_max, kro_max = p["krw_max"], p["kro_max"]
    denom = max(EPS, (1.0 - swc - sor))
    sw_norm = np.clip((sw_local - swc) / denom, 0.0, 1.0)
    so_norm = np.clip((so_local - sor) / denom, 0.0, 1.0)
    krw_local = krw_max * (sw_norm ** nw)
    kro_local = kro_max * (so_norm ** no)
    return krw_local, kro_local


def fractional_flow_np(Sw: np.ndarray, p: dict, eps: float = EPS) -> np.ndarray:
    So = 1.0 - Sw
    mu_w, mu_o = p["mu_w"], p["mu_o"]
    krw, kro = calculate_relative_permeability_np(Sw, So, p)
    viscosity_ratio = mu_w / mu_o
    perm_term = kro / (krw + eps)
    return 1.0 / (1.0 + viscosity_ratio * perm_term)


def dfw_dsw_np(Sw: np.ndarray, p: dict):
    fw = fractional_flow_np(Sw, p)
    d_fw = np.gradient(fw, Sw)
    return d_fw, fw


def welge_tangent(Sw_grid: np.ndarray, fw: np.ndarray, swc: float, eps: float = EPS):
    Sw = Sw_grid.astype(float)
    slopes = np.full_like(Sw, -np.inf, dtype=float)
    denom = Sw - swc
    valid = denom > 0.0
    slopes[valid] = fw[valid] / (denom[valid] + eps)
    diffs = np.diff(slopes)
    neg_idx = np.where(diffs < 0.0)[0]
    if len(neg_idx) > 0:
        tangent_idx = int(neg_idx[0])
    else:
        tangent_idx = int(np.argmax(slopes))
    Sw_star = float(Sw[tangent_idx])
    fw_star = float(fw[tangent_idx])
    slope_star = float(slopes[tangent_idx])
    return Sw_star, fw_star, slope_star, tangent_idx


def calculate_x_sw(i_w, t, phi, A, derivative):
    return ((FT3_PER_BBL * i_w * t) / (phi * A)) * derivative


def profile_at_time(
    t_days: float,
    p: dict,
    Sw_grid: np.ndarray | None = None,
    add_plateau_points: int = 12,
):
    validate_params(p)
    injector_at_left = bool(p.get("injector_at_left", True))

    if Sw_grid is None:
        Sw_grid = np.linspace(p["swc"], 1.0 - p["sor"], 200)

    d_fw, fw = dfw_dsw_np(Sw_grid, p)
    Sw_star, fw_star, slope_star, i_star = welge_tangent(
        Sw_grid, fw, p["swc"]
    )

    x_sw = calculate_x_sw(
        p["i_w"], t_days, p["phi"], p["A"], d_fw
    )
    xD = np.clip(x_sw / p["x_ip"], 0.0, 1.0)

    start_idx = int(i_star)
    end_idx = len(Sw_grid) - 1
    front_x_D = float(xD[start_idx])

    x_left = xD[start_idx:end_idx + 1]
    S_left = Sw_grid[start_idx:end_idx + 1]

    ord_left = np.argsort(x_left)
    x_left = x_left[ord_left]
    S_left = S_left[ord_left]

    if x_left[0] > 0.0:
        x_left = np.insert(x_left, 0, 0.0)
        S_left = np.insert(S_left, 0, 1.0 - p["sor"])

    x_right = np.linspace(front_x_D, 1.0, add_plateau_points)
    S_right = np.full_like(x_right, p["swc"])

    x_shock = np.array([front_x_D, front_x_D], dtype=float)
    S_shock = np.array([p["swc"], Sw_star], dtype=float)

    xD_full = np.concatenate([x_left, x_right])
    Sw_full = np.concatenate([S_left, S_right])

    if not injector_at_left:
        xD_full = 1.0 - xD_full
        x_left = 1.0 - x_left
        x_right = 1.0 - x_right
        x_shock = 1.0 - x_shock
        front_x_D = 1.0 - front_x_D

    order = np.argsort(xD_full)
    xD_full = np.clip(xD_full[order], 0.0, 1.0)
    Sw_full = Sw_full[order]

    C = (FT3_PER_BBL * p["i_w"]) / (
        p["phi"] * p["A"] * p["x_ip"]
    )
    t_D = C * t_days

    meta = {
        "Sw_star": float(Sw_star),
        "xD_shock": float(front_x_D),
        "t_days": float(t_days),
        "t_D": float(t_D),
        "segments": {
            "rarefaction_left": (x_left, S_left),
            "shock_vertical": (x_shock, S_shock),
            "plateau_right": (x_right, S_right),
        },
    }
    return xD_full, Sw_full, meta


def build_fan_profiles(times_days, p: dict):
    out = []
    for t in times_days:
        _, _, meta = profile_at_time(float(t), p)
        xD_star = float(meta["xD_shock"])
        Sw_star = float(meta["Sw_star"])
        x_left, S_left = meta["segments"]["rarefaction_left"]

        xi = np.asarray(x_left, dtype=float) / max(EPS, xD_star)
        xi = np.clip(xi, 0.0, 1.0)

        out.append({
            "t_days": float(meta["t_days"]),
            "t_D": float(meta["t_D"]),
            "xi": xi.astype(np.float32),
            "Sw_fan_true": np.asarray(S_left, dtype=np.float32),
            "xD_star": xD_star,
            "Sw_star": Sw_star,
        })
    return out


def breakthrough_time_days(p: dict) -> float:
    validate_params(p)
    Sw_grid = np.linspace(p["swc"], 1.0 - p["sor"], 400)
    d_fw, fw = dfw_dsw_np(Sw_grid, p)
    Sw_star, fw_star, slope_star, i_star = welge_tangent(
        Sw_grid, fw, p["swc"]
    )

    Sw_at_fw1 = p["swc"] + 1.0 / max(EPS, slope_star)
    Q_iBT = Sw_at_fw1 - p["swc"]

    PV_rb = (p["phi"] * p["A"] * p["x_ip"]) / FT3_PER_BBL
    bw = float(p.get("bw", 1.02))
    PV_STB = PV_rb / bw
    W_iBT = Q_iBT * PV_STB
    t_BT = W_iBT / p["i_w"]
    return float(t_BT)


def make_fan_anchors_from_truth(
    xi: np.ndarray,
    Sw_fan_true: np.ndarray,
    swc: float,
    sor: float,
    Sw_star: float,
    k_interior=(0.25, 0.60),
):
    xi = np.asarray(xi)
    Sw_fan_true = np.asarray(Sw_fan_true)
    n = len(xi)

    if n < 2:
        return (
            np.array([0], np.int32),
            np.array([1.0 - sor], np.float32),
        )

    i0 = 0
    iend = n - 1
    i1 = max(1, min(n - 2, int(round(k_interior[0] * (n - 1)))))
    i2 = max(i1 + 1, min(n - 2, int(round(k_interior[1] * (n - 1)))))

    idxs = [i0, i1, i2, iend]
    targs = [
        1.0 - sor,
        float(Sw_fan_true[i1]),
        float(Sw_fan_true[i2]),
        float(Sw_star),
    ]

    uniq, idxs_out, targs_out = set(), [], []
    for ix, tv in sorted(zip(idxs, targs), key=lambda z: z[0]):
        if ix not in uniq:
            uniq.add(ix)
            idxs_out.append(int(ix))
            targs_out.append(float(tv))

    return (
        np.array(idxs_out, np.int32),
        np.array(targs_out, np.float32),
    )


def generate_param_grid(base_p: dict):
    no_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    nw_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    sor_vals = np.arange(0.10, 0.40 + 1e-9, 0.10, dtype=np.float32)
    swc_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)
    mu_o_vals = np.arange(0.3, 1.0 + 1e-9, 0.1, dtype=np.float32)
    mu_w_vals = np.arange(0.5, 50.0 + 1e-9, 5.5, dtype=np.float32)
    phi_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)

    param_grid = []

    for no, nw, swc, sor, mu_w, mu_o, phi in itertools.product(
        no_vals,
        nw_vals,
        swc_vals,
        sor_vals,
        mu_w_vals,
        mu_o_vals,
        phi_vals,
    ):
        p = dict(base_p)
        p["no"] = float(no)
        p["nw"] = float(nw)
        p["swc"] = float(swc)
        p["sor"] = float(sor)
        p["mu_w"] = float(mu_w)
        p["mu_o"] = float(mu_o)
        p["phi"] = float(phi)

        try:
            validate_params(p)
        except AssertionError:
            continue

        param_grid.append(p)

    return param_grid


def build_multi_case_fan_arrays(param_list, num_times=6, t_min_days=100.0):
    xi_list_all = []
    Sw_list_all = []
    p10_list_all = []
    tD_list_all = []
    anchor_idxs_all = []
    anchor_targs_all = []

    max_T = 0
    max_K = 0

    n_cases = len(param_list)
    t0 = time.time()

    for icase, p in enumerate(param_list, start=1):
        t_bt = breakthrough_time_days(p)
        if t_bt <= t_min_days:
            continue

        times = np.linspace(t_min_days, t_bt, num_times).tolist()
        fan_profiles = build_fan_profiles(times, p)

        for prof in fan_profiles:
            xi = np.asarray(prof["xi"], dtype=np.float32)
            Sw_true = np.asarray(prof["Sw_fan_true"], dtype=np.float32)
            tD = float(prof["t_D"])
            xD_star = float(prof["xD_star"])
            Sw_star = float(prof["Sw_star"])

            max_T = max(max_T, len(xi))

            idxs_np, targs_np = make_fan_anchors_from_truth(
                xi,
                Sw_true,
                swc=float(p["swc"]),
                sor=float(p["sor"]),
                Sw_star=Sw_star,
            )
            max_K = max(max_K, idxs_np.shape[0])

            p10 = np.array([
                p["no"], p["nw"], p["swc"], p["sor"],
                p["mu_w"], p["mu_o"], p["phi"],
                tD, xD_star, Sw_star,
            ], dtype=np.float32)

            xi_list_all.append(xi)
            Sw_list_all.append(Sw_true)
            p10_list_all.append(p10)
            tD_list_all.append(tD)
            anchor_idxs_all.append(idxs_np)
            anchor_targs_all.append(targs_np)

        if icase % 1000 == 0 or icase == n_cases:
            elapsed = time.time() - t0
            print(
                f"  analytical dataset progress: {icase:>6}/{n_cases} cases "
                f"| profiles={len(xi_list_all):>7} | {elapsed:.1f}s"
            )

    if not xi_list_all:
        raise RuntimeError("No valid fan profiles generated.")

    def pad_seq(arr, L):
        pad = L - len(arr)
        if pad <= 0:
            return arr[:L]
        return np.pad(arr, (0, pad), mode="edge")

    def pad_anchor(arr, L):
        pad = L - len(arr)
        if pad <= 0:
            return arr[:L]
        return np.pad(arr, (0, pad), mode="edge")

    xi_all = np.stack(
        [pad_seq(xi, max_T).reshape(-1, 1) for xi in xi_list_all],
        axis=0,
    ).astype(np.float32)

    Sw_all = np.stack(
        [pad_seq(Sw, max_T).reshape(-1, 1) for Sw in Sw_list_all],
        axis=0,
    ).astype(np.float32)

    p10_all = np.stack(p10_list_all, axis=0).astype(np.float32)
    tD_all = np.array(tD_list_all, dtype=np.float32)

    anchor_idxs_all = np.stack(
        [pad_anchor(v, max_K) for v in anchor_idxs_all],
        axis=0,
    ).astype(np.int32)

    anchor_targs_all = np.stack(
        [pad_anchor(v, max_K) for v in anchor_targs_all],
        axis=0,
    ).astype(np.float32)

    return (
        xi_all,
        Sw_all,
        p10_all,
        tD_all,
        anchor_idxs_all,
        anchor_targs_all,
    )


# =============================================================================
# PyTorch model: framework-equivalent port of Keras Stage-1
# =============================================================================

class PIRNNFanXPU(nn.Module):
    def __init__(self):
        super().__init__()

        # Explicit separate LSTM layers mirror the Keras stack.
        self.lstm1 = nn.LSTM(
            input_size=1 + PARAM_DIM,
            hidden_size=HIDDEN,
            num_layers=1,
            batch_first=True,
        )
        self.lstm2 = nn.LSTM(
            input_size=HIDDEN,
            hidden_size=HIDDEN,
            num_layers=1,
            batch_first=True,
        )
        self.out = nn.Linear(HIDDEN, 1)

        self._keras_like_init()

    @staticmethod
    def _init_lstm_like_keras(lstm: nn.LSTM):
        # Keras defaults:
        # kernel_initializer = glorot_uniform
        # recurrent_initializer = orthogonal
        # bias_initializer = zeros
        # unit_forget_bias = True
        for name, param in lstm.named_parameters():
            if "weight_ih" in name:
                fan_in = param.shape[1]
                fan_out = param.shape[0]
                limit = math.sqrt(6.0 / (fan_in + fan_out))
                nn.init.uniform_(param, -limit, limit)

            elif "weight_hh" in name:
                nn.init.orthogonal_(param)

            elif "bias_ih" in name:
                nn.init.zeros_(param)
                h = param.numel() // 4
                with torch.no_grad():
                    # PyTorch gate order: i, f, g, o
                    param[h:2*h].fill_(1.0)

            elif "bias_hh" in name:
                nn.init.zeros_(param)

    def _keras_like_init(self):
        self._init_lstm_like_keras(self.lstm1)
        self._init_lstm_like_keras(self.lstm2)

        fan_in = self.out.weight.shape[1]
        fan_out = self.out.weight.shape[0]
        limit = math.sqrt(6.0 / (fan_in + fan_out))
        nn.init.uniform_(self.out.weight, -limit, limit)
        nn.init.zeros_(self.out.bias)

    def forward(self, xi_seq, p_vec):
        # xi_seq: [B,T,1], p_vec: [B,10]
        T = xi_seq.shape[1]
        p_rep = p_vec.unsqueeze(1).expand(-1, T, -1)
        z = torch.cat([xi_seq, p_rep], dim=-1)

        y, _ = self.lstm1(z)
        y, _ = self.lstm2(y)
        z_raw = self.out(y)

        swc = p_rep[:, :, 2:3]
        sor = p_rep[:, :, 3:4]
        span = torch.clamp(1.0 - swc - sor, min=1e-8)

        return swc + span * torch.sigmoid(z_raw)


# =============================================================================
# PyTorch loss port
# =============================================================================

def fractional_flow_torch(S, p_vec):
    nw = p_vec[:, 1:2].unsqueeze(1)
    no = p_vec[:, 0:1].unsqueeze(1)
    swc = p_vec[:, 2:3].unsqueeze(1)
    sor = p_vec[:, 3:4].unsqueeze(1)
    mu_w = p_vec[:, 4:5].unsqueeze(1)
    mu_o = p_vec[:, 5:6].unsqueeze(1)

    denom = torch.clamp(1.0 - swc - sor, min=1e-8)
    Se = torch.clamp((S - swc) / denom, min=0.0, max=1.0)

    krw = 0.8 * torch.pow(Se, nw)
    kro = 0.8 * torch.pow(1.0 - Se, no)

    M = mu_w / mu_o
    return 1.0 / (1.0 + M * (kro / (krw + EPS)))


def data_loss(S_pred, S_true):
    return torch.mean((S_pred - S_true) ** 2)


def injector_bc_loss(S_pred, p_vec):
    sor = p_vec[:, 3:4]
    S_left = S_pred[:, 0, 0:1]
    target_left = 1.0 - sor
    return torch.mean((S_left - target_left) ** 2)


def tip_bc_loss(S_pred, p_vec):
    Sw_star = p_vec[:, -1:]
    S_tip = S_pred[:, -1, 0:1]
    return torch.mean((S_tip - Sw_star) ** 2)


def physics_loss_char(xi_seq, S_pred, t_D, p_vec):
    fw = fractional_flow_torch(S_pred, p_vec)

    dfdS = torch.autograd.grad(
        outputs=fw,
        inputs=S_pred,
        grad_outputs=torch.ones_like(fw),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]

    xD_star = p_vec[:, -2:-1].unsqueeze(1)
    t_D = t_D.reshape(-1, 1, 1)

    res = xi_seq * xD_star - t_D * dfdS
    if res.shape[1] > 2:
        res = res[:, 1:-1, :]

    return torch.mean(res ** 2)


def shape_loss(S_pred, S_true):
    grad = torch.abs(S_true[:, 1:, :] - S_true[:, :-1, :])
    grad = torch.cat(
        [grad, torch.zeros_like(grad[:, :1, :])],
        dim=1,
    )
    w = 1.0 + 10.0 * grad / (torch.max(grad) + 1e-12)
    return torch.mean(w * (S_pred - S_true) ** 2)


def monotonicity_loss(S_pred):
    dS = S_pred[:, 1:, :] - S_pred[:, :-1, :]
    viol = torch.relu(dS)
    return torch.mean(viol ** 2)


def anchor_loss(S_pred, idxs, targs):
    S = S_pred[..., 0]
    selected = torch.gather(S, 1, idxs.long())
    return torch.mean((selected - targs) ** 2)


def total_losses(model, xi, Sw, p10, tD, ai, at):
    S_pred = model(xi, p10)

    Ld = data_loss(S_pred, Sw)
    Lp = physics_loss_char(xi, S_pred, tD, p10)
    Lbc = injector_bc_loss(S_pred, p10)
    Ltip = tip_bc_loss(S_pred, p10)
    La = anchor_loss(S_pred, ai, at)
    Lmono = monotonicity_loss(S_pred)

    if LAMBDA_SHAPE != 0.0:
        Lshape = shape_loss(S_pred, Sw)
    else:
        Lshape = torch.zeros((), device=S_pred.device, dtype=S_pred.dtype)

    total = (
        LAMBDA_DATA * Ld
        + LAMBDA_PHYS * Lp
        + LAMBDA_BC * Lbc
        + LAMBDA_TIP * Ltip
        + LAMBDA_ANCHOR * La
        + LAMBDA_MONO * Lmono
        + LAMBDA_SHAPE * Lshape
    )

    parts = {
        "data": Ld,
        "physics": Lp,
        "bc_inj": Lbc,
        "bc_tip": Ltip,
        "anchor": La,
        "mono": Lmono,
        "shape": Lshape,
        "total": total,
    }
    return S_pred, parts


# =============================================================================
# Dataset cache
# =============================================================================

def build_or_load_dataset(force_rebuild=False):
    if DATASET.exists() and DATASET_META.exists() and not force_rebuild:
        meta = read_json(DATASET_META)

        if (
            meta.get("source_sha256") == SOURCE_SHA
            and meta.get("seed") == SEED
            and meta.get("num_times") == 6
            and meta.get("t_min_days") == 100.0
        ):
            print("\nLOADING CACHED ANALYTICAL DATASET")
            d = np.load(DATASET)
            arrays = (
                d["xi"],
                d["Sw"],
                d["p10"],
                d["tD"],
                d["ai"],
                d["at"],
            )
            print("  dataset:", DATASET)
            print("  SHA-256:", sha256(DATASET))
            print("  xi shape:", arrays[0].shape)
            return arrays

    print("\nBUILDING ANALYTICAL DATASET ON CPU")
    print("  Note: this preprocessing is NumPy/CPU; XPU acceleration begins at training.")

    param_list = generate_param_grid(BASE_P)
    print("  parameter cases:", len(param_list))

    t0 = time.time()
    arrays = build_multi_case_fan_arrays(
        param_list,
        num_times=6,
        t_min_days=100.0,
    )
    elapsed = time.time() - t0

    xi, Sw, p10, tD, ai, at = arrays

    np.savez_compressed(
        DATASET,
        xi=xi,
        Sw=Sw,
        p10=p10,
        tD=tD,
        ai=ai,
        at=at,
    )

    meta = {
        "artifact": "V16E Stage-1 analytical fan dataset cache",
        "source_path": rel(SOURCE),
        "source_sha256": SOURCE_SHA,
        "seed": SEED,
        "num_times": 6,
        "t_min_days": 100.0,
        "parameter_case_count": len(param_list),
        "profile_count": int(xi.shape[0]),
        "xi_shape": list(xi.shape),
        "Sw_shape": list(Sw.shape),
        "p10_shape": list(p10.shape),
        "build_seconds": elapsed,
        "dataset_sha256": sha256(DATASET),
    }
    DATASET_META.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print("\nANALYTICAL DATASET CACHED")
    print("  profiles :", xi.shape[0])
    print("  xi shape :", xi.shape)
    print("  SHA-256  :", sha256(DATASET))

    return arrays


# =============================================================================
# XPU smoke test
# =============================================================================

def xpu_smoke_test(device):
    print("\nXPU LSTM SMOKE TEST")

    test_lstm = nn.LSTM(
        input_size=11,
        hidden_size=64,
        num_layers=2,
        batch_first=True,
    ).to(device)

    x = torch.randn(8, 32, 11, device=device, requires_grad=True)
    y, _ = test_lstm(x)
    loss = (y ** 2).mean()
    loss.backward()
    sync_xpu()

    passed = (
        y.device.type == "xpu"
        and x.grad is not None
        and torch.isfinite(y).all().item()
        and torch.isfinite(x.grad).all().item()
    )

    print("  output device:", y.device)
    print("  forward/backward:", "PASS" if passed else "FAIL")

    del test_lstm, x, y, loss
    if hasattr(torch.xpu, "empty_cache"):
        torch.xpu.empty_cache()

    if not passed:
        raise RuntimeError("Intel XPU LSTM forward/backward smoke test failed.")


# =============================================================================
# Training
# =============================================================================

def train_xpu(
    model,
    arrays,
    device,
    microbatch,
    max_epochs=None,
):
    xi_all, Sw_all, p10_all, tD_all, ai_all, at_all = arrays

    N = xi_all.shape[0]

    split_rng = np.random.default_rng(SEED)
    idx = np.arange(N)
    split_rng.shuffle(idx)

    N_train = int(0.8 * N)
    train_idx = idx[:N_train]
    holdout_idx = idx[N_train:]

    epochs = EPOCHS if max_epochs is None else int(max_epochs)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    history = {
        "epoch": [],
        "data": [],
        "physics": [],
        "bc_inj": [],
        "bc_tip": [],
        "anchor": [],
        "mono": [],
        "shape": [],
        "total": [],
        "epoch_seconds": [],
    }

    print("\nXPU TRAINING")
    print("  device             :", device)
    print("  train profiles     :", len(train_idx))
    print("  holdout profiles   :", len(holdout_idx))
    print("  logical batch      :", LOGICAL_BATCH)
    print("  XPU microbatch     :", microbatch)
    print("  optimizer updates/epoch:",
          math.ceil(len(train_idx) / LOGICAL_BATCH))
    print("  epochs             :", epochs)
    print("  mixed precision    : OFF")

    global_t0 = time.time()

    for epoch in range(1, epochs + 1):
        epoch_t0 = time.time()

        # Deterministic changing order each epoch.
        erng = np.random.default_rng(SEED + epoch)
        order = train_idx.copy()
        erng.shuffle(order)

        accum = {
            "data": 0.0,
            "physics": 0.0,
            "bc_inj": 0.0,
            "bc_tip": 0.0,
            "anchor": 0.0,
            "mono": 0.0,
            "shape": 0.0,
            "total": 0.0,
        }
        count_samples = 0

        for b0 in range(0, len(order), LOGICAL_BATCH):
            logical_idx = order[b0:b0 + LOGICAL_BATCH]
            logical_n = len(logical_idx)

            optimizer.zero_grad(set_to_none=True)

            for m0 in range(0, logical_n, microbatch):
                mids = logical_idx[m0:m0 + microbatch]
                m = len(mids)

                xi = torch.from_numpy(xi_all[mids]).to(device)
                Sw = torch.from_numpy(Sw_all[mids]).to(device)
                p10 = torch.from_numpy(p10_all[mids]).to(device)
                tD = torch.from_numpy(tD_all[mids]).to(device)
                ai = torch.from_numpy(ai_all[mids]).to(device)
                at = torch.from_numpy(at_all[mids]).to(device)

                _, parts = total_losses(
                    model, xi, Sw, p10, tD, ai, at
                )

                # Preserve the mean-gradient of the original logical batch.
                scale = float(m) / float(logical_n)
                (parts["total"] * scale).backward()

                for k in accum:
                    accum[k] += float(parts[k].detach().cpu()) * m

                count_samples += m

                del xi, Sw, p10, tD, ai, at, parts

            optimizer.step()

        sync_xpu()

        n = max(1, count_samples)
        epoch_seconds = time.time() - epoch_t0

        history["epoch"].append(epoch)
        for k in (
            "data", "physics", "bc_inj", "bc_tip",
            "anchor", "mono", "shape", "total",
        ):
            history[k].append(accum[k] / n)
        history["epoch_seconds"].append(epoch_seconds)

        if (
            epoch == 1
            or epoch % 10 == 0
            or epoch == epochs
        ):
            elapsed = time.time() - global_t0
            print(
                f"[XPU] Epoch {epoch:04d}/{epochs} "
                f"| Data {history['data'][-1]:.3e} "
                f"| Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} "
                f"| Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} "
                f"| Mono {history['mono'][-1]:.3e} "
                f"| {epoch_seconds:.2f}s/epoch "
                f"| total {elapsed:.1f}s"
            )

    return history, train_idx, holdout_idx


# =============================================================================
# Evaluation
# =============================================================================

@torch.no_grad()
def predict_array(model, xi, p10, device, batch=1024):
    preds = []
    for i0 in range(0, len(xi), batch):
        x = torch.from_numpy(xi[i0:i0 + batch]).to(device)
        p = torch.from_numpy(p10[i0:i0 + batch]).to(device)
        y = model(x, p)
        preds.append(y.cpu().numpy())
    return np.concatenate(preds, axis=0)


def holdout_metrics(model, arrays, holdout_idx, device):
    xi_all, Sw_all, p10_all, tD_all, ai_all, at_all = arrays

    total_sq = 0.0
    total_abs = 0.0
    total_n = 0
    max_abs = 0.0
    lower_viol = 0
    upper_viol = 0
    finite = True

    batch = 1024

    for i0 in range(0, len(holdout_idx), batch):
        ids = holdout_idx[i0:i0 + batch]

        with torch.no_grad():
            x = torch.from_numpy(xi_all[ids]).to(device)
            p = torch.from_numpy(p10_all[ids]).to(device)
            pred = model(x, p).cpu().numpy()

        truth = Sw_all[ids]
        err = pred - truth
        abs_err = np.abs(err)

        finite = (
            finite
            and bool(np.isfinite(pred).all())
            and bool(np.isfinite(err).all())
        )

        total_sq += float(np.sum(err * err))
        total_abs += float(np.sum(abs_err))
        total_n += int(err.size)
        max_abs = max(max_abs, float(np.max(abs_err)))

        swc = p10_all[ids, 2].reshape(-1, 1, 1)
        sor = p10_all[ids, 3].reshape(-1, 1, 1)

        lower_viol += int(np.sum(pred < swc - 1e-7))
        upper_viol += int(np.sum(pred > (1.0 - sor) + 1e-7))

    mse = total_sq / max(total_n, 1)

    return {
        "mse": mse,
        "rmse": math.sqrt(mse),
        "mae": total_abs / max(total_n, 1),
        "max_abs_error": max_abs,
        "finite_predictions": finite,
        "lower_bound_violations": lower_viol,
        "upper_bound_violations": upper_viol,
        "bounds_pass": lower_viol == 0 and upper_viol == 0,
        "n_scalar_predictions": total_n,
    }


def make_case_from_values(
    base_p,
    no,
    nw,
    swc,
    sor,
    mu_w,
    mu_o,
    phi,
):
    p = dict(base_p)
    p["no"] = float(no)
    p["nw"] = float(nw)
    p["swc"] = float(swc)
    p["sor"] = float(sor)
    p["mu_w"] = float(mu_w)
    p["mu_o"] = float(mu_o)
    p["phi"] = float(phi)
    validate_params(p)
    return p


@torch.no_grad()
def predict_profile_fan(model, p_case, t_days, device):
    fan = build_fan_profiles([t_days], p_case)[0]

    xi = fan["xi"].astype(np.float32)
    t_D = float(fan["t_D"])
    xD_star = float(fan["xD_star"])
    Sw_star = float(fan["Sw_star"])

    p10 = np.array([[
        p_case["no"], p_case["nw"],
        p_case["swc"], p_case["sor"],
        p_case["mu_w"], p_case["mu_o"],
        p_case["phi"],
        t_D, xD_star, Sw_star,
    ]], dtype=np.float32)

    x = torch.from_numpy(xi.reshape(1, -1, 1)).to(device)
    p = torch.from_numpy(p10).to(device)

    Sw_fan_pred = model(x, p).cpu().numpy().squeeze()

    xD_fan = xi * xD_star
    xD_pred = np.concatenate([xD_fan, [xD_star, 1.0]])
    Sw_pred = np.concatenate([
        Sw_fan_pred,
        [p_case["swc"], p_case["swc"]],
    ])

    xD_true, Sw_true, meta = profile_at_time(t_days, p_case)

    return {
        "xD_true": xD_true,
        "Sw_true": Sw_true,
        "xD_pred": xD_pred,
        "Sw_pred": Sw_pred,
        "t_days": float(t_days),
        "t_D": t_D,
        "xD_star_true": float(meta["xD_shock"]),
    }


def evaluate_case(model, p_case, device):
    t_bt = breakthrough_time_days(p_case)
    times = np.linspace(100.0, t_bt, 15).tolist()

    rows = []

    common_x = np.linspace(0.0, 1.0, 200)
    residuals_all = []
    truths_all = []
    preds_all = []

    for t in times:
        r = predict_profile_fan(model, p_case, float(t), device)

        pred_interp = np.interp(
            r["xD_true"],
            r["xD_pred"],
            r["Sw_pred"],
        )
        err = pred_interp - r["Sw_true"]

        rows.append({
            "t_days": r["t_days"],
            "t_D": r["t_D"],
            "xD_star_true": r["xD_star_true"],
            "mse": float(np.mean(err ** 2)),
            "mae": float(np.mean(np.abs(err))),
            "max_abs_err": float(np.max(np.abs(err))),
        })

        true_common = np.interp(
            common_x,
            r["xD_true"],
            r["Sw_true"],
        )
        pred_common = np.interp(
            common_x,
            r["xD_pred"],
            r["Sw_pred"],
        )

        residuals_all.append(pred_common - true_common)
        truths_all.append(true_common)
        preds_all.append(pred_common)

    residuals = np.asarray(residuals_all)
    truths = np.asarray(truths_all)
    preds = np.asarray(preds_all)

    rf = residuals.ravel()
    tf = truths.ravel()
    pf = preds.ravel()

    ss_res = float(np.sum((tf - pf) ** 2))
    ss_tot = float(np.sum((tf - np.mean(tf)) ** 2))
    r2 = 1.0 - ss_res / max(ss_tot, EPS)

    shapiro_p = None
    try:
        from scipy import stats
        sample = rf
        if len(sample) > 5000:
            sample = sample[:5000]
        shapiro_p = float(stats.shapiro(sample).pvalue)
    except Exception:
        pass

    diagnostics = {
        "mean_residual": float(np.mean(rf)),
        "std_residual": float(np.std(rf)),
        "max_abs_residual": float(np.max(np.abs(rf))),
        "r_squared": float(r2),
        "shapiro_p_optional": shapiro_p,
        "n_evaluation_points": int(len(rf)),
    }

    return {
        "breakthrough_time_days": float(t_bt),
        "rows": rows,
        "diagnostics": diagnostics,
    }


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--microbatch",
        type=int,
        default=512,
        help="XPU microbatch; gradients accumulate to logical batch 8192.",
    )
    parser.add_argument(
        "--force-rebuild-dataset",
        action="store_true",
        help="Ignore cached analytical dataset and rebuild it.",
    )
    parser.add_argument(
        "--smoke-epochs",
        type=int,
        default=0,
        help=(
            "Optional short engineering smoke run. "
            "0 means full frozen 400 epochs. "
            "A smoke run is NOT certifiable."
        ),
    )
    args = parser.parse_args()

    print("=" * 80)
    print("PAD-Stream V16E-1B1-XPU")
    print("Final Incompressible BL PI-RNN Native-Coordinate XPU Reproduction")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print()

    if SUMMARY.exists():
        raise RuntimeError(
            "Certified XPU summary already exists. Refusing to overwrite."
        )

    # -------------------------------------------------------------------------
    # Pre-execution scientific authority gates
    # -------------------------------------------------------------------------

    gates = {
        "E1A_source_SHA_valid": valid_sha(E1A_SOURCE_SHA),
        "E1A_protocol_SHA_valid": valid_sha(E1A_PROTOCOL_SHA),
        "E1A_issues_SHA_valid": valid_sha(E1A_ISSUES_SHA),
        "E1A_artifacts_SHA_valid": valid_sha(E1A_ARTIFACTS_SHA),
        "E1A_handoff_SHA_valid": valid_sha(E1A_HANDOFF_SHA),
        "E1A_summary_SHA_valid": valid_sha(E1A_SUMMARY_SHA),

        "E1A_source_SHA_exact": exact_sha(E1A_SOURCE, E1A_SOURCE_SHA),
        "E1A_protocol_SHA_exact": exact_sha(E1A_PROTOCOL, E1A_PROTOCOL_SHA),
        "E1A_issues_SHA_exact": exact_sha(E1A_ISSUES, E1A_ISSUES_SHA),
        "E1A_artifacts_SHA_exact": exact_sha(E1A_ARTIFACTS, E1A_ARTIFACTS_SHA),
        "E1A_handoff_SHA_exact": exact_sha(E1A_HANDOFF, E1A_HANDOFF_SHA),
        "E1A_summary_SHA_exact": exact_sha(E1A_SUMMARY, E1A_SUMMARY_SHA),

        "Stage1_source_SHA_exact": exact_sha(SOURCE, SOURCE_SHA),

        # Prevent an unnoticed second "authoritative" reproduction after the
        # standard TF run has already certified.
        "TensorFlow_E1B1_not_already_certified":
            not TF_E1B1_SUMMARY.exists(),
    }

    if E1A_SUMMARY.exists():
        e1a = read_json(E1A_SUMMARY)
        gates["E1A_status_exact"] = (
            e1a.get("status") == EXPECTED_E1A_STATUS
        )
        gates["E1A_INC_authorized"] = (
            e1a.get("authorized_next_experiment")
            == "V16E-BLREP-INC-001"
        )
    else:
        gates["E1A_status_exact"] = False
        gates["E1A_INC_authorized"] = False

    print("SCIENTIFIC AUTHORITY GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "XPU reproduction blocked before execution by scientific authority gate."
        )

    # -------------------------------------------------------------------------
    # Prospective framework-port protocol is written BEFORE seeing results.
    # -------------------------------------------------------------------------

    port_protocol = {
        "milestone": "V16E-1B1-XPU",
        "experiment_id": EXPERIMENT_ID,
        "protocol_timing":
            "Written before analytical dataset evaluation/training results.",

        "classification":
            "FRAMEWORK_EQUIVALENT_ACCELERATION_PORT",

        "not_claimed": [
            "bitwise TensorFlow reproduction",
            "historical checkpoint recovery",
            "OOD experiment",
            "TOF model",
            "PhysicsNeMo model",
        ],

        "frozen_scientific_equivalence": {
            "source_sha256": SOURCE_SHA,
            "teacher":
                "analytical Buckley-Leverett rarefaction + Welge tangent/shock",
            "coordinate": "xi = xD/xD_star",
            "conditioning_order": CONDITIONING,
            "conditioning_dim": PARAM_DIM,
            "architecture":
                "sequence xi + repeated p10 -> LSTM64 -> LSTM64 -> Dense1 -> "
                "sigmoid range map [swc,1-sor]",
            "optimizer": "Adam",
            "learning_rate": LR,
            "logical_batch_size": LOGICAL_BATCH,
            "gradient_accumulation":
                "XPU microbatches are sample-weighted and accumulated before "
                "one optimizer step per logical batch.",
            "epochs": EPOCHS,
            "seed": SEED,
            "mixed_precision": False,
            "loss_weights": {
                "data": LAMBDA_DATA,
                "physics": LAMBDA_PHYS,
                "injector_bc": LAMBDA_BC,
                "tip_bc": LAMBDA_TIP,
                "anchor": LAMBDA_ANCHOR,
                "monotonicity": LAMBDA_MONO,
                "shape": LAMBDA_SHAPE,
            },
        },

        "framework_difference":
            "PyTorch XPU kernels and Keras/TensorFlow kernels are not expected "
            "to be bitwise identical. This branch tests scientific/model "
            "equivalence under the same frozen equations and architecture.",

        "acceptance_policy":
            "No numerical cutoff invented. Require successful full run, finite "
            "source-native metrics, saturation bounds, source-case diagnostics, "
            "XPU execution, and immutable artifact hashes.",
    }
    PORT_PROTOCOL.write_text(
        json.dumps(port_protocol, indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # XPU environment and smoke test
    # -------------------------------------------------------------------------

    print("\nRUNTIME")
    print("  PyTorch:", torch.__version__)
    print("  torch.xpu available:", torch.xpu.is_available())
    print("  XPU count:", torch.xpu.device_count() if torch.xpu.is_available() else 0)

    if not torch.xpu.is_available():
        raise RuntimeError("torch.xpu.is_available() is False.")

    device = torch.device("xpu")
    torch.manual_seed(SEED)

    xpu_smoke_test(device)

    # -------------------------------------------------------------------------
    # Dataset
    # -------------------------------------------------------------------------

    arrays = build_or_load_dataset(
        force_rebuild=args.force_rebuild_dataset
    )

    xi_all, Sw_all, p10_all, tD_all, ai_all, at_all = arrays

    if p10_all.shape[1] != PARAM_DIM:
        raise RuntimeError(
            f"Dataset p10 dim={p10_all.shape[1]}, expected {PARAM_DIM}"
        )

    # -------------------------------------------------------------------------
    # Model
    # -------------------------------------------------------------------------

    torch.manual_seed(SEED)
    model = PIRNNFanXPU().to(device)

    param_device_types = {p.device.type for p in model.parameters()}
    if param_device_types != {"xpu"}:
        raise RuntimeError(
            f"Model parameters are not exclusively on XPU: {param_device_types}"
        )

    # -------------------------------------------------------------------------
    # Config
    # -------------------------------------------------------------------------

    full_certification_run = args.smoke_epochs == 0
    actual_epochs = EPOCHS if full_certification_run else args.smoke_epochs

    config = {
        "experiment_id": EXPERIMENT_ID,
        "framework": "PyTorch XPU",
        "pytorch_version": torch.__version__,
        "device": str(device),

        "source_sha256": SOURCE_SHA,
        "framework_port_protocol_sha256": sha256(PORT_PROTOCOL),

        "coordinate": "xi = xD/xD_star",
        "condition_on": CONDITIONING,
        "param_dim": PARAM_DIM,
        "hidden": HIDDEN,
        "layers": LAYERS,

        "seed": SEED,
        "optimizer": "Adam",
        "learning_rate": LR,
        "logical_batch_size": LOGICAL_BATCH,
        "microbatch": args.microbatch,
        "epochs_requested": actual_epochs,
        "full_certification_run": full_certification_run,
        "mixed_precision": False,

        "dataset": {
            "path": rel(DATASET),
            "sha256": sha256(DATASET),
            "cached": True,
        },
    }
    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Train
    # -------------------------------------------------------------------------

    history, train_idx, holdout_idx = train_xpu(
        model=model,
        arrays=arrays,
        device=device,
        microbatch=args.microbatch,
        max_epochs=actual_epochs,
    )

    HISTORY.write_text(
        json.dumps(jsonable(history), indent=2),
        encoding="utf-8",
    )

    # Save checkpoint
    torch.save(
        {
            "experiment_id": EXPERIMENT_ID,
            "source_sha256": SOURCE_SHA,
            "model_state_dict": model.state_dict(),
            "conditioning": CONDITIONING,
            "param_dim": PARAM_DIM,
            "hidden": HIDDEN,
            "layers": LAYERS,
            "framework": "PyTorch XPU",
            "pytorch_version": torch.__version__,
        },
        CHECKPOINT,
    )

    # Engineering smoke runs stop here and are deliberately not certifiable.
    if not full_certification_run:
        print("\nSMOKE RUN COMPLETE")
        print(
            "This was an engineering smoke run only. "
            "It is NOT a certifiable V16E reproduction."
        )
        print("Checkpoint:", CHECKPOINT)
        print("Checkpoint SHA-256:", sha256(CHECKPOINT))
        return

    # -------------------------------------------------------------------------
    # Evaluate
    # -------------------------------------------------------------------------

    print("\nSOURCE-NATIVE HOLDOUT EVALUATION")
    holdout = holdout_metrics(
        model,
        arrays,
        holdout_idx,
        device,
    )

    print(f"  MSE     : {holdout['mse']:.12e}")
    print(f"  RMSE    : {holdout['rmse']:.12e}")
    print(f"  MAE     : {holdout['mae']:.12e}")
    print(f"  Max |e| : {holdout['max_abs_error']:.12e}")
    print("  Bounds  :", "PASS" if holdout["bounds_pass"] else "FAIL")

    p_case_1 = make_case_from_values(
        BASE_P,
        no=2.0, nw=2.0,
        swc=0.20, sor=0.20,
        mu_w=0.5, mu_o=0.7,
        phi=0.20,
    )

    p_case_2 = make_case_from_values(
        BASE_P,
        no=3.0, nw=2.0,
        swc=0.15, sor=0.25,
        mu_w=6.0, mu_o=0.9,
        phi=0.25,
    )

    print("\nSOURCE CASE DIAGNOSTICS")
    case1 = evaluate_case(model, p_case_1, device)
    case2 = evaluate_case(model, p_case_2, device)

    print(
        "  Case 1 R2:",
        f"{case1['diagnostics']['r_squared']:.8f}",
        "| max residual:",
        f"{case1['diagnostics']['max_abs_residual']:.6e}",
    )
    print(
        "  Case 2 R2:",
        f"{case2['diagnostics']['r_squared']:.8f}",
        "| max residual:",
        f"{case2['diagnostics']['max_abs_residual']:.6e}",
    )

    metrics = {
        "experiment_id": EXPERIMENT_ID,
        "classification": "FRAMEWORK_EQUIVALENT_XPU_REPRODUCTION",
        "evaluation_semantics":
            "Source-native reproduction holdout and source-defined analytical "
            "case diagnostics. NOT OOD.",

        "dataset": {
            "path": rel(DATASET),
            "sha256": sha256(DATASET),
            "profile_count": int(xi_all.shape[0]),
            "train_profile_count": int(len(train_idx)),
            "holdout_profile_count": int(len(holdout_idx)),
            "xi_shape": list(xi_all.shape),
            "p10_shape": list(p10_all.shape),
        },

        "holdout": holdout,
        "case_1_symmetric": case1,
        "case_2_asymmetric": case2,

        "training": {
            "epochs_completed": len(history["epoch"]),
            "logical_batch_size": LOGICAL_BATCH,
            "microbatch": args.microbatch,
            "final_losses": {
                k: (
                    history[k][-1]
                    if k != "epoch"
                    else history["epoch"][-1]
                )
                for k in history
                if k != "epoch_seconds"
            },
            "mean_epoch_seconds":
                float(np.mean(history["epoch_seconds"])),
        },

        "threshold_policy":
            "No numerical acceptance threshold invented or applied.",
    }

    METRICS.write_text(
        json.dumps(jsonable(metrics), indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Gates
    # -------------------------------------------------------------------------

    case1_rows_finite = all(
        finite_number(r["mse"])
        and finite_number(r["mae"])
        and finite_number(r["max_abs_err"])
        for r in case1["rows"]
    )

    case2_rows_finite = all(
        finite_number(r["mse"])
        and finite_number(r["mae"])
        and finite_number(r["max_abs_err"])
        for r in case2["rows"]
    )

    gates.update({
        "PyTorch_XPU_available": torch.xpu.is_available(),
        "model_parameters_on_XPU": param_device_types == {"xpu"},
        "full_400_epochs_completed": len(history["epoch"]) == EPOCHS,

        "checkpoint_written":
            CHECKPOINT.exists() and CHECKPOINT.stat().st_size > 0,
        "config_written":
            CONFIG.exists() and CONFIG.stat().st_size > 0,
        "port_protocol_written":
            PORT_PROTOCOL.exists() and PORT_PROTOCOL.stat().st_size > 0,
        "history_written":
            HISTORY.exists() and HISTORY.stat().st_size > 0,
        "metrics_written":
            METRICS.exists() and METRICS.stat().st_size > 0,

        "holdout_predictions_finite":
            bool(holdout["finite_predictions"]),
        "holdout_bounds_pass":
            bool(holdout["bounds_pass"]),
        "holdout_metrics_finite":
            all(
                finite_number(holdout[k])
                for k in ("mse", "rmse", "mae", "max_abs_error")
            ),

        "case1_metrics_finite": case1_rows_finite,
        "case2_metrics_finite": case2_rows_finite,
        "case1_diagnostics_finite":
            finite_number(case1["diagnostics"]["r_squared"])
            and finite_number(case1["diagnostics"]["max_abs_residual"]),
        "case2_diagnostics_finite":
            finite_number(case2["diagnostics"]["r_squared"])
            and finite_number(case2["diagnostics"]["max_abs_residual"]),

        "framework_difference_explicitly_recorded": True,
        "bitwise_TensorFlow_equivalence_not_claimed": True,
        "no_mixed_precision": True,
        "no_TOF_transformation": True,
        "no_OOD_claim": True,
        "EXP_CS1_not_modified": True,
        "geology0029_not_reopened": True,
        "no_invented_numeric_threshold": True,
    })

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "classification": "FRAMEWORK_EQUIVALENT_XPU_REPRODUCTION",
        "historical_checkpoint_recovery": False,

        "source": {
            "path": rel(SOURCE),
            "sha256": SOURCE_SHA,
        },

        "framework": {
            "name": "PyTorch XPU",
            "version": torch.__version__,
            "device": str(device),
            "bitwise_TensorFlow_equivalence_claimed": False,
        },

        "scientific_equivalence": {
            "teacher": "analytical BL + Welge tangent/shock",
            "coordinate": "xi=xD/xD_star",
            "conditioning_order": CONDITIONING,
            "architecture_topology":
                "xi+p10 -> LSTM64 -> LSTM64 -> Dense1 -> sigmoid range_map",
            "logical_batch_size": LOGICAL_BATCH,
            "epochs": EPOCHS,
            "seed": SEED,
            "loss_weights": port_protocol[
                "frozen_scientific_equivalence"
            ]["loss_weights"],
        },

        "artifacts": {
            "dataset": {
                "path": rel(DATASET),
                "sha256": sha256(DATASET),
            },
            "port_protocol": {
                "path": rel(PORT_PROTOCOL),
                "sha256": sha256(PORT_PROTOCOL),
            },
            "checkpoint": {
                "path": rel(CHECKPOINT),
                "sha256": sha256(CHECKPOINT),
            },
            "config": {
                "path": rel(CONFIG),
                "sha256": sha256(CONFIG),
            },
            "history": {
                "path": rel(HISTORY),
                "sha256": sha256(HISTORY),
            },
            "metrics": {
                "path": rel(METRICS),
                "sha256": sha256(METRICS),
            },
        },

        "firewall": {
            "TOF": False,
            "OOD": False,
            "mixed_precision": False,
            "PhysicsNeMo": False,
            "EXP_CS1_retraining": False,
            "geology0029_reopening": False,
        },
    }

    MANIFEST.write_text(
        json.dumps(jsonable(manifest), indent=2),
        encoding="utf-8",
    )

    gates["manifest_written"] = (
        MANIFEST.exists() and MANIFEST.stat().st_size > 0
    )
    gates["manifest_checkpoint_SHA_exact"] = (
        read_json(MANIFEST)["artifacts"]["checkpoint"]["sha256"]
        == sha256(CHECKPOINT)
    )
    gates["manifest_metrics_SHA_exact"] = (
        read_json(MANIFEST)["artifacts"]["metrics"]["sha256"]
        == sha256(METRICS)
    )

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B1_XPU_FINAL_INCOMPRESSIBLE_BL_PI_RNN_"
        "FRAMEWORK_EQUIVALENT_NATIVE_COORDINATE_REPRODUCTION_COMPLETE_"
        "INTEL_XPU_EXECUTION_CONFIRMED_NEW_CHECKPOINT_SHA_BOUND_"
        "SOURCE_NATIVE_HOLDOUT_AND_ANALYTICAL_DIAGNOSTICS_FINITE_"
        "SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
        "COMPRESSIBLE_XPU_PORT_PROTOCOL_AUTHORIZED"
        if ok else
        "V16E1B1_XPU_REPRODUCTION_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B1-XPU",
        "experiment_id": EXPERIMENT_ID,
        "status": status,

        "framework": "PyTorch XPU",
        "pytorch_version": torch.__version__,
        "source_sha256": SOURCE_SHA,

        "dataset_sha256": sha256(DATASET),
        "port_protocol_sha256": sha256(PORT_PROTOCOL),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "config_sha256": sha256(CONFIG),
        "history_sha256": sha256(HISTORY),
        "metrics_sha256": sha256(METRICS),
        "manifest_sha256": sha256(MANIFEST),

        "holdout_mse": holdout["mse"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mae": holdout["mae"],
        "holdout_max_abs_error": holdout["max_abs_error"],

        "bitwise_TensorFlow_equivalence_claimed": False,
        "scientific_framework_equivalence_claimed": bool(ok),
        "OOD_claim": False,
        "TOF_transformation_used": False,

        "next_milestone": (
            "V16E-1B2-XPU — Compressible BL PI-RNN framework-equivalent "
            "native-coordinate XPU reproduction protocol/port"
            if ok else
            "V16E-1B1-XPU-R1 — diagnose failed gate"
        ),

        "gates": {k: bool(v) for k, v in gates.items()},
    }

    SUMMARY.write_text(
        json.dumps(jsonable(summary), indent=2),
        encoding="utf-8",
    )

    print("\nFINAL GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    print("\nSTATUS")
    print(" ", status)

    print("\nARTIFACT HASHES")
    print("  Dataset      :", sha256(DATASET))
    print("  Port protocol:", sha256(PORT_PROTOCOL))
    print("  Checkpoint   :", sha256(CHECKPOINT))
    print("  Config       :", sha256(CONFIG))
    print("  History      :", sha256(HISTORY))
    print("  Metrics      :", sha256(METRICS))
    print("  Manifest     :", sha256(MANIFEST))
    print("  Summary      :", sha256(SUMMARY))

    print("\nNEXT")
    print(" ", summary["next_milestone"])

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
