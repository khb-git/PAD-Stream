#!/usr/bin/env python3
"""
PAD-Stream V16E-1B2-XPU
Final Compressible BL PI-RNN Framework-Equivalent Native-Coordinate XPU Reproduction

Experiment
----------
V16E-BLREP-COMP-XPU-001

Purpose
-------
Reproduce the frozen final Stage-2 compressible Buckley-Leverett PI-RNN on the
Intel XPU using a controlled PyTorch framework-equivalent port.

Frozen Stage-2 authority
------------------------
pi_rnn_stage2_compressible_godunov.py
SHA-256:
1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397

The scientific model remains:
  xi sequence + repeated 11-d conditioning
      -> LSTM(64)
      -> LSTM(64)
      -> Dense(1)
      -> sigmoid range map [swc, 1-sor]

Conditioning:
  [no, nw, swc/swi, sor, mu_w, mu_o, phi,
   tD, xD_star, Sw_star, Nc]

Teacher:
  conservative finite-volume compressible Godunov solver
  u(x_D) = u_inj exp(Nc x_D)

Physics residual:
  R = y(xi*xD_star; Nc) - tD * dfw/dSw
  y(x;Nc) = -expm1(-Nc*x)/Nc
  with the exact Nc -> 0 limit y=x.

Source-native dataset:
  Nc grid = [0, 0.05, 0.10, 0.20, 0.30]
  max_cases = 2400 seeded case/Nc combinations
  NX_TRAIN = 1601
  n_fan = 64
  six times from 100 d to 0.95 t_BT
  80/20 seeded reproduction split
  logical training batch = 8192
  epochs = 400
  seed = 1337

Evaluation:
  NX_REF = 3201 fine-grid Godunov truth
  Stage-1 nesting diagnostics at Nc=0
  compressible diagnostics
  Nc accuracy sweep

Framework policy
----------------
This is NOT bitwise TensorFlow reproduction. It is a framework-equivalent
PyTorch/XPU reproduction of the frozen physics, teacher, architecture, losses,
conditioning and logical batch semantics.

The Godunov teacher cases may be scheduled in parallel on CPU. Parallelization
does not alter the selected seeded cases, equations, grid, snapshots, or output
ordering.

NO TOF transformation.
NO OOD claim.
NO mixed precision.
NO PhysicsNeMo.
EXP-CS1 remains closed.
geology0029 remains consumed.
"""

from __future__ import annotations

from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
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
# Paths / immutable authority
# =============================================================================

R = Path(__file__).resolve().parent

EXPERIMENT_ID = "V16E-BLREP-COMP-XPU-001"

OUT = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / EXPERIMENT_ID
)
OUT.mkdir(parents=True, exist_ok=True)

DATASET_DIR = R / "output" / "V16_E1B_XPU_DATASETS"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

DATASET = DATASET_DIR / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.npz"
DATASET_META = DATASET_DIR / "V16E_STAGE2_COMPRESSIBLE_GODUNOV_DATASET_SEED1337.json"

CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_001.pt"
SMOKE_CHECKPOINT = OUT / "V16E_BLREP_COMP_XPU_001_SMOKE.pt"
CONFIG = OUT / "V16E_BLREP_COMP_XPU_001_Config.json"
PORT_PROTOCOL = OUT / "V16E_BLREP_COMP_XPU_001_Framework_Port_Protocol.json"
HISTORY = OUT / "V16E_BLREP_COMP_XPU_001_Training_History.json"
METRICS = OUT / "V16E_BLREP_COMP_XPU_001_Metrics.json"
MANIFEST = OUT / "V16E_BLREP_COMP_XPU_001_Manifest.json"
SUMMARY = OUT / "PAD_Stream_V16E1B2_XPU_Summary.json"

SOURCE = R / "pi_rnn_stage2_compressible_godunov.py"
SOURCE_SHA = "1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397"

# Certified upstream E1B1-XPU-R1
B1_R1_SOURCE = R / "PAD_Stream_V16E1B1_XPU_R1_PostTraining_Evaluation_Repair.py"
B1_R1_SOURCE_SHA = "c6ecf40bbdbf0df5e613c54ae4df0eb9e4e171affecccee34a0c11606df77637"

B1_DIR = (
    R / "output"
    / "V16_E1B_XPU_NATIVE_BL_REPRODUCTIONS"
    / "V16E-BLREP-INC-XPU-001"
)
B1_CHECKPOINT = B1_DIR / "V16E_BLREP_INC_XPU_001.pt"
B1_METRICS = B1_DIR / "V16E_BLREP_INC_XPU_001_Metrics.json"
B1_REPAIR = B1_DIR / "V16E_BLREP_INC_XPU_001_R1_Evaluation_Repair.json"
B1_MANIFEST = B1_DIR / "V16E_BLREP_INC_XPU_001_Manifest.json"
B1_SUMMARY = B1_DIR / "PAD_Stream_V16E1B1_XPU_R1_Summary.json"

B1_CHECKPOINT_SHA = "535e106b59a8064979f525290882fc3280e79fa1d27cdb73edcc9805f6932bc4"
B1_METRICS_SHA = "871b1f676a1f3309adee39616c1570ce4349d7e0ac12f1552eb6dcb80f91f77e"
B1_REPAIR_SHA = "aee86a41af7e981407b29c6328b1022fc229c35e6a6a4961c74e141611afb12b"
B1_MANIFEST_SHA = "1ae5006f7df286326e8da034794dde1f1e0166160b5ac20a6ab2cf2f7431da73"
B1_SUMMARY_SHA = "a92cad56025ff276146793206367ac1adc13fbbd5f7fb22d8bc5ad8d85ac3ac7"

EXPECTED_B1_STATUS = (
    "V16E1B1_XPU_R1_POSTTRAINING_EVALUATION_REPAIR_CERTIFIED_"
    "FULL_400_EPOCH_XPU_TRAINING_PRESERVED_CHECKPOINT_UNCHANGED_"
    "MODEL_EVAL_INFERENCE_REPAIR_APPLIED_"
    "SOURCE_NATIVE_HOLDOUT_AND_ANALYTICAL_DIAGNOSTICS_FINITE_"
    "SATURATION_BOUNDS_PASS_NO_OOD_NO_TOF_"
    "V16E1B2_XPU_COMPRESSIBLE_PORT_AUTHORIZED"
)


# =============================================================================
# Frozen Stage-2 constants
# =============================================================================

FT3_PER_BBL = 5.615
EPS = 1e-12

NX_TRAIN = 1601
NX_REF = 3201

SEED = 1337
EPOCHS = 400
LR = 1e-3

HIDDEN = 64
LAYERS = 2
PARAM_DIM = 11

LOGICAL_BATCH = 8192
DEFAULT_MICROBATCH = 2048

LAMBDA_DATA = 1.0
LAMBDA_PHYS = 0.05
LAMBDA_BC = 5.0
LAMBDA_TIP = 5.0
LAMBDA_ANCHOR = 10.0
LAMBDA_MONO = 0.2
LAMBDA_SHAPE = 0.0

NC_VALS = np.array([0.0, 0.05, 0.10, 0.20, 0.30], dtype=np.float32)

CONDITIONING = [
    "no", "nw", "swi", "sor",
    "mu_w", "mu_o", "phi",
    "tD", "xD_star", "Sw_star", "Nc",
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
# Helpers
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and path.is_file() and sha256(path) == expected


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(R))
    except ValueError:
        return str(path)


def finite_number(v) -> bool:
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def jsonable(v):
    if isinstance(v, dict):
        return {str(k): jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [jsonable(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.integer, np.floating, np.bool_)):
        return v.item()
    if isinstance(v, Path):
        return str(v)
    return v


def sync_xpu():
    if torch.xpu.is_available():
        torch.xpu.synchronize()


# =============================================================================
# Frozen rock-fluid / analytical functions
# =============================================================================

REQUIRED_KEYS = (
    "nw", "no", "mu_w", "mu_o", "swc", "sor",
    "krw_max", "kro_max", "phi", "A", "x_ip", "i_w",
)


def validate_params(p: dict):
    missing = [k for k in REQUIRED_KEYS if k not in p]
    if missing:
        raise KeyError(f"Missing required parameters: {missing}")

    assert 0 <= p["swc"] < 1
    assert 0 <= p["sor"] < 1
    assert p["swc"] + p["sor"] < 1
    assert p["mu_w"] > 0 and p["mu_o"] > 0
    assert p["nw"] > 0 and p["no"] > 0
    assert 0 < p["krw_max"] <= 1
    assert 0 < p["kro_max"] <= 1
    assert 0 < p["phi"] < 1
    assert p["A"] > 0 and p["x_ip"] > 0 and p["i_w"] > 0


def relative_perm_np(Sw: np.ndarray, p: dict):
    So = 1.0 - Sw
    denom = max(EPS, 1.0 - p["swc"] - p["sor"])

    sw_norm = np.clip((Sw - p["swc"]) / denom, 0.0, 1.0)
    so_norm = np.clip((So - p["sor"]) / denom, 0.0, 1.0)

    krw = p["krw_max"] * sw_norm ** p["nw"]
    kro = p["kro_max"] * so_norm ** p["no"]
    return krw, kro


def fractional_flow_np(Sw: np.ndarray, p: dict):
    krw, kro = relative_perm_np(Sw, p)
    return 1.0 / (
        1.0
        + (p["mu_w"] / p["mu_o"]) * (kro / (krw + EPS))
    )


def dfw_dsw_np(Sw: np.ndarray, p: dict):
    fw = fractional_flow_np(Sw, p)
    return np.gradient(fw, Sw), fw


def welge_tangent(Sw_grid: np.ndarray, fw: np.ndarray, swc: float):
    Sw = Sw_grid.astype(float)
    slopes = np.full_like(Sw, -np.inf, dtype=float)
    denom = Sw - swc
    valid = denom > 0
    slopes[valid] = fw[valid] / (denom[valid] + EPS)

    diffs = np.diff(slopes)
    neg_idx = np.where(diffs < 0)[0]

    tangent_idx = int(neg_idx[0]) if len(neg_idx) else int(np.argmax(slopes))

    return (
        float(Sw[tangent_idx]),
        float(fw[tangent_idx]),
        float(slopes[tangent_idx]),
        tangent_idx,
    )


# =============================================================================
# Stage-2 compressibility / travel-time transform
# =============================================================================

def y_of_x(xD, Nc: float):
    xD = np.asarray(xD, dtype=float)
    if abs(Nc) < 1e-12:
        return xD.copy()
    return -np.expm1(-Nc * xD) / Nc


def Y_L(Nc: float) -> float:
    return float(y_of_x(1.0, Nc))


def breakthrough_time_days(p: dict, Nc: float = 0.0) -> float:
    validate_params(p)

    Sw_grid = np.linspace(p["swc"], 1.0 - p["sor"], 400)
    _, fw = dfw_dsw_np(Sw_grid, p)
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

    return float(t_BT * Y_L(Nc))


# =============================================================================
# Exact conservative Godunov teacher
# =============================================================================

def godunov_compressible_snapshots(
    p: dict,
    Nc: float,
    times_days,
    nx: int = NX_TRAIN,
    cfl: float = 0.4,
):
    validate_params(p)

    L = p["x_ip"]
    xD = np.linspace(0.0, 1.0, nx)
    dx = L / (nx - 1)

    u_inj = FT3_PER_BBL * p["i_w"] / p["A"]
    u = u_inj * np.exp(Nc * xD)
    u_face = 0.5 * (u[:-1] + u[1:])

    sw_init = p["swc"] + 1e-3
    sw_inj = 1.0 - p["sor"] - 1e-3
    f_inj = fractional_flow_np(np.array([sw_inj]), p)[0]

    Sg = np.linspace(p["swc"], 1.0 - p["sor"], 400)
    dfw, _ = dfw_dsw_np(Sg, p)
    dt_cfl = (
        cfl * p["phi"] * dx
        / (u.max() * np.abs(dfw).max() + EPS)
    )

    S = np.full(nx, sw_init)
    S[0] = sw_inj
    F = np.empty(nx + 1)

    snapshots = []
    t_now = 0.0

    for t_target in sorted(float(t) for t in times_days):
        span_t = t_target - t_now

        if span_t <= 0:
            snapshots.append(S.copy())
            continue

        nt = max(1, int(np.ceil(span_t / dt_cfl)))
        dt = span_t / nt

        for _ in range(nt):
            f = fractional_flow_np(S, p)

            F[0] = u[0] * f_inj
            F[1:nx] = u_face * f[:-1]
            F[nx] = u[-1] * f[-1]

            S[1:] -= (
                dt / (p["phi"] * dx)
            ) * (F[2:] - F[1:-1])

            S[0] = sw_inj
            np.clip(S, p["swc"], 1.0 - p["sor"], out=S)

        t_now = t_target
        snapshots.append(S.copy())

    return xD, snapshots


def godunov_front_crossing(xD: np.ndarray, S: np.ndarray, level: float):
    below = np.where(S < level)[0]
    if len(below) == 0 or below[0] == 0:
        return float("nan")

    i = below[0]
    return float(
        np.interp(
            level,
            [S[i], S[i - 1]],
            [xD[i], xD[i - 1]],
        )
    )


def godunov_front_from_profile(
    xD: np.ndarray,
    S: np.ndarray,
    Sw_star: float,
    swc: float,
):
    return godunov_front_crossing(
        xD,
        S,
        swc + 0.5 * (Sw_star - swc),
    )


def build_fan_profiles_godunov(
    times_days,
    p: dict,
    Nc: float = 0.0,
    n_fan: int = 64,
    nx: int = NX_TRAIN,
):
    grid = np.linspace(p["swc"], 1.0 - p["sor"], 800)
    _, fw = dfw_dsw_np(grid, p)
    Sw_star, _, _, _ = welge_tangent(grid, fw, p["swc"])

    C = (
        FT3_PER_BBL * p["i_w"]
        / (p["phi"] * p["A"] * p["x_ip"])
    )

    xD_sol, snaps = godunov_compressible_snapshots(
        p, Nc, times_days, nx=nx
    )

    out = []
    nf = int(n_fan)

    for t, S_sol in zip(
        sorted(float(t) for t in times_days),
        snaps,
    ):
        x_star = godunov_front_from_profile(
            xD_sol,
            S_sol,
            Sw_star,
            p["swc"],
        )

        if not np.isfinite(x_star) or x_star <= 0:
            continue

        xi = np.linspace(0.0, 1.0, nf)
        S_fan = np.interp(xi * x_star, xD_sol, S_sol)

        S_fan = np.maximum(S_fan, Sw_star)
        S_fan[0] = 1.0 - p["sor"]
        S_fan[-1] = Sw_star

        out.append({
            "t_days": float(t),
            "t_D": float(C * t),
            "Nc": float(Nc),
            "xi": xi.astype(np.float32),
            "Sw_fan_true": S_fan.astype(np.float32),
            "xD_star": float(x_star),
            "Sw_star": float(Sw_star),
        })

    return out


# =============================================================================
# Parameter grid / exact seeded 2400-combo selection
# =============================================================================

def generate_param_grid():
    no_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    nw_vals = np.arange(2.0, 4.0 + 1e-9, 1.0, dtype=np.float32)
    sor_vals = np.arange(0.10, 0.40 + 1e-9, 0.10, dtype=np.float32)
    swc_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)
    mu_o_vals = np.arange(0.3, 1.0 + 1e-9, 0.1, dtype=np.float32)
    mu_w_vals = np.arange(0.5, 50.0 + 1e-9, 5.5, dtype=np.float32)
    phi_vals = np.arange(0.10, 0.30 + 1e-9, 0.10, dtype=np.float32)

    out = []

    for no, nw, swc, sor, mu_w, mu_o, phi in itertools.product(
        no_vals,
        nw_vals,
        swc_vals,
        sor_vals,
        mu_w_vals,
        mu_o_vals,
        phi_vals,
    ):
        p = dict(BASE_P)
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

        out.append(p)

    return out


def selected_combos():
    param_list = generate_param_grid()
    combos = [
        (p, float(nc))
        for p in param_list
        for nc in NC_VALS
    ]

    rng = np.random.default_rng(SEED)
    pick = rng.choice(
        len(combos),
        size=2400,
        replace=False,
    )

    return [combos[i] for i in pick], len(param_list), len(combos)


def make_fan_anchors_from_truth(
    xi: np.ndarray,
    Sw_fan_true: np.ndarray,
    swc: float,
    sor: float,
    Sw_star: float,
    k_interior=(0.25, 0.60),
):
    n = len(xi)

    if n < 2:
        return (
            np.array([0], dtype=np.int32),
            np.array([1.0 - sor], dtype=np.float32),
        )

    i0 = 0
    iend = n - 1
    i1 = max(
        1,
        min(n - 2, int(round(k_interior[0] * (n - 1)))),
    )
    i2 = max(
        i1 + 1,
        min(n - 2, int(round(k_interior[1] * (n - 1)))),
    )

    idxs = [i0, i1, i2, iend]
    targs = [
        1.0 - sor,
        float(Sw_fan_true[i1]),
        float(Sw_fan_true[i2]),
        float(Sw_star),
    ]

    return (
        np.array(idxs, dtype=np.int32),
        np.array(targs, dtype=np.float32),
    )


# =============================================================================
# Parallel-safe worker
# =============================================================================

def _godunov_combo_worker(task):
    combo_index, p, nc = task

    t_bt = breakthrough_time_days(p, Nc=nc)

    if 0.95 * t_bt <= 100.0:
        return combo_index, []

    times = np.linspace(
        100.0,
        0.95 * t_bt,
        6,
    ).tolist()

    profiles = build_fan_profiles_godunov(
        times,
        p,
        Nc=nc,
        n_fan=64,
        nx=NX_TRAIN,
    )

    rows = []

    for prof in profiles:
        xi = np.asarray(prof["xi"], dtype=np.float32)
        Sw_true = np.asarray(
            prof["Sw_fan_true"],
            dtype=np.float32,
        )

        tD = float(prof["t_D"])
        xD_star = float(prof["xD_star"])
        Sw_star = float(prof["Sw_star"])

        ai, at = make_fan_anchors_from_truth(
            xi,
            Sw_true,
            swc=float(p["swc"]),
            sor=float(p["sor"]),
            Sw_star=Sw_star,
        )

        p11 = np.array([
            p["no"], p["nw"],
            p["swc"], p["sor"],
            p["mu_w"], p["mu_o"],
            p["phi"],
            tD, xD_star, Sw_star,
            nc,
        ], dtype=np.float32)

        rows.append(
            (xi, Sw_true, p11, tD, ai, at)
        )

    return combo_index, rows


# =============================================================================
# Dataset cache
# =============================================================================

def build_or_load_dataset(force=False, workers=8):
    if DATASET.exists() and DATASET_META.exists() and not force:
        meta = read_json(DATASET_META)

        if (
            meta.get("source_sha256") == SOURCE_SHA
            and meta.get("seed") == SEED
            and meta.get("NX_TRAIN") == NX_TRAIN
            and meta.get("max_cases") == 2400
            and meta.get("nc_vals") == NC_VALS.tolist()
        ):
            print("\nLOADING CACHED STAGE-2 GODUNOV DATASET")
            d = np.load(DATASET)

            arrays = (
                d["xi"],
                d["Sw"],
                d["p11"],
                d["tD"],
                d["ai"],
                d["at"],
            )

            print("  dataset :", DATASET)
            print("  SHA-256 :", sha256(DATASET))
            print("  xi shape:", arrays[0].shape)
            print("  p11     :", arrays[2].shape)

            return arrays

    combos, parameter_case_count, total_combo_count = selected_combos()

    print("\nBUILDING STAGE-2 GODUNOV TEACHER DATASET ON CPU")
    print("  parameter cases             :", parameter_case_count)
    print("  full case/Nc combinations   :", total_combo_count)
    print("  frozen selected combinations:", len(combos))
    print("  NX_TRAIN                    :", NX_TRAIN)
    print("  workers                     :", workers)
    print(
        "  Parallel workers schedule independent frozen Godunov cases; "
        "result order remains source-selected order."
    )

    tasks = [
        (i, p, nc)
        for i, (p, nc) in enumerate(combos)
    ]

    t0 = time.time()

    if workers <= 1:
        results = []
        for n, task in enumerate(tasks, start=1):
            results.append(_godunov_combo_worker(task))
            if n % 100 == 0 or n == len(tasks):
                print(
                    f"  teacher progress: {n:>4}/{len(tasks)} "
                    f"| elapsed={time.time()-t0:.1f}s"
                )
    else:
        results = []
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for n, result in enumerate(
                ex.map(_godunov_combo_worker, tasks, chunksize=1),
                start=1,
            ):
                results.append(result)

                if n % 100 == 0 or n == len(tasks):
                    print(
                        f"  teacher progress: {n:>4}/{len(tasks)} "
                        f"| elapsed={time.time()-t0:.1f}s"
                    )

    # executor.map preserves task order. Keep an explicit proof.
    order_ok = all(result[0] == i for i, result in enumerate(results))
    if not order_ok:
        raise RuntimeError("Parallel Godunov result ordering changed.")

    rows = []
    for _, combo_rows in results:
        rows.extend(combo_rows)

    if not rows:
        raise RuntimeError("No Stage-2 Godunov profiles generated.")

    xi = np.stack(
        [r[0].reshape(-1, 1) for r in rows],
        axis=0,
    ).astype(np.float32)

    Sw = np.stack(
        [r[1].reshape(-1, 1) for r in rows],
        axis=0,
    ).astype(np.float32)

    p11 = np.stack(
        [r[2] for r in rows],
        axis=0,
    ).astype(np.float32)

    tD = np.asarray(
        [r[3] for r in rows],
        dtype=np.float32,
    )

    ai = np.stack(
        [r[4] for r in rows],
        axis=0,
    ).astype(np.int32)

    at = np.stack(
        [r[5] for r in rows],
        axis=0,
    ).astype(np.float32)

    np.savez_compressed(
        DATASET,
        xi=xi,
        Sw=Sw,
        p11=p11,
        tD=tD,
        ai=ai,
        at=at,
    )

    meta = {
        "artifact": "V16E Stage-2 compressible Godunov dataset",
        "source_path": rel(SOURCE),
        "source_sha256": SOURCE_SHA,
        "seed": SEED,

        "parameter_case_count": parameter_case_count,
        "full_combo_count": total_combo_count,
        "max_cases": 2400,
        "nc_vals": NC_VALS.tolist(),

        "NX_TRAIN": NX_TRAIN,
        "n_fan": 64,
        "num_times": 6,
        "t_min_days": 100.0,
        "horizon": "0.95*t_BT",

        "parallel_workers_used": workers,
        "parallel_output_order_preserved": order_ok,

        "profile_count": int(xi.shape[0]),
        "xi_shape": list(xi.shape),
        "Sw_shape": list(Sw.shape),
        "p11_shape": list(p11.shape),

        "build_seconds": float(time.time() - t0),
        "dataset_sha256": sha256(DATASET),
    }

    DATASET_META.write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )

    print("\nSTAGE-2 GODUNOV DATASET CACHED")
    print("  profiles :", xi.shape[0])
    print("  xi       :", xi.shape)
    print("  p11      :", p11.shape)
    print("  SHA-256  :", sha256(DATASET))

    return xi, Sw, p11, tD, ai, at


# =============================================================================
# XPU model
# =============================================================================

class CompressiblePIRNNXPU(nn.Module):
    def __init__(self):
        super().__init__()

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
    def _init_lstm(lstm):
        for name, param in lstm.named_parameters():
            if "weight_ih" in name:
                fan_in = param.shape[1]
                fan_out = param.shape[0]
                limit = math.sqrt(
                    6.0 / (fan_in + fan_out)
                )
                nn.init.uniform_(param, -limit, limit)

            elif "weight_hh" in name:
                nn.init.orthogonal_(param)

            elif "bias_ih" in name:
                nn.init.zeros_(param)
                h = param.numel() // 4
                with torch.no_grad():
                    # PyTorch: input, forget, cell, output
                    param[h:2*h].fill_(1.0)

            elif "bias_hh" in name:
                nn.init.zeros_(param)

    def _keras_like_init(self):
        self._init_lstm(self.lstm1)
        self._init_lstm(self.lstm2)

        fan_in = self.out.weight.shape[1]
        fan_out = self.out.weight.shape[0]
        limit = math.sqrt(
            6.0 / (fan_in + fan_out)
        )

        nn.init.uniform_(
            self.out.weight,
            -limit,
            limit,
        )
        nn.init.zeros_(self.out.bias)

    def forward(self, xi_seq, p_vec):
        T = xi_seq.shape[1]
        p_rep = p_vec.unsqueeze(1).expand(-1, T, -1)

        z = torch.cat(
            [xi_seq, p_rep],
            dim=-1,
        )

        y, _ = self.lstm1(z)
        y, _ = self.lstm2(y)
        raw = self.out(y)

        swc = p_rep[:, :, 2:3]
        sor = p_rep[:, :, 3:4]

        span = torch.clamp(
            1.0 - swc - sor,
            min=1e-8,
        )

        return swc + span * torch.sigmoid(raw)


# =============================================================================
# PyTorch loss port
# =============================================================================

def fractional_flow_torch(S, p11):
    no = p11[:, 0:1].unsqueeze(1)
    nw = p11[:, 1:2].unsqueeze(1)
    swc = p11[:, 2:3].unsqueeze(1)
    sor = p11[:, 3:4].unsqueeze(1)
    mu_w = p11[:, 4:5].unsqueeze(1)
    mu_o = p11[:, 5:6].unsqueeze(1)

    denom = torch.clamp(
        1.0 - swc - sor,
        min=1e-8,
    )

    Se = torch.clamp(
        (S - swc) / denom,
        min=0.0,
        max=1.0,
    )

    krw = 0.8 * torch.pow(Se, nw)
    kro = 0.8 * torch.pow(1.0 - Se, no)

    M = mu_w / mu_o

    return 1.0 / (
        1.0 + M * (kro / (krw + EPS))
    )


def data_loss(S_pred, S_true):
    return torch.mean(
        (S_pred - S_true) ** 2
    )


def injector_bc_loss(S_pred, p11):
    sor = p11[:, 3:4]
    S_left = S_pred[:, 0, 0:1]
    return torch.mean(
        (S_left - (1.0 - sor)) ** 2
    )


def tip_bc_loss(S_pred, p11):
    # Frozen Stage-2 fixed index: Sw_star = index 9, not -1 (Nc).
    Sw_star = p11[:, 9:10]
    S_tip = S_pred[:, -1, 0:1]
    return torch.mean(
        (S_tip - Sw_star) ** 2
    )


def physics_loss_char(
    xi_seq,
    S_pred,
    t_D,
    p11,
):
    fw = fractional_flow_torch(
        S_pred,
        p11,
    )

    dfdS = torch.autograd.grad(
        outputs=fw,
        inputs=S_pred,
        grad_outputs=torch.ones_like(fw),
        create_graph=True,
        retain_graph=True,
        only_inputs=True,
    )[0]

    # Frozen Stage-2 fixed indices.
    xD_star = p11[:, 8:9].unsqueeze(1)
    Nc = p11[:, 10:11].unsqueeze(1)
    t_D = t_D.reshape(-1, 1, 1)

    xD = xi_seq * xD_star

    small = torch.abs(Nc) < 1e-8
    Nc_safe = torch.where(
        small,
        torch.ones_like(Nc),
        Nc,
    )

    y = torch.where(
        small,
        xD,
        -torch.expm1(-Nc_safe * xD) / Nc_safe,
    )

    res = y - t_D * dfdS

    if res.shape[1] > 2:
        res = res[:, 1:-1, :]

    return torch.mean(res ** 2)


def monotonicity_loss(S_pred):
    dS = S_pred[:, 1:, :] - S_pred[:, :-1, :]
    return torch.mean(
        torch.relu(dS) ** 2
    )


def anchor_loss(S_pred, ai, at):
    S = S_pred[..., 0]
    selected = torch.gather(
        S,
        1,
        ai.long(),
    )
    return torch.mean(
        (selected - at) ** 2
    )


def total_losses(
    model,
    xi,
    Sw,
    p11,
    tD,
    ai,
    at,
):
    S_pred = model(xi, p11)

    Ld = data_loss(S_pred, Sw)
    Lp = physics_loss_char(
        xi,
        S_pred,
        tD,
        p11,
    )
    Lbc = injector_bc_loss(
        S_pred,
        p11,
    )
    Ltip = tip_bc_loss(
        S_pred,
        p11,
    )
    La = anchor_loss(
        S_pred,
        ai,
        at,
    )
    Lmono = monotonicity_loss(
        S_pred,
    )

    total = (
        LAMBDA_DATA * Ld
        + LAMBDA_PHYS * Lp
        + LAMBDA_BC * Lbc
        + LAMBDA_TIP * Ltip
        + LAMBDA_ANCHOR * La
        + LAMBDA_MONO * Lmono
    )

    return S_pred, {
        "data": Ld,
        "physics": Lp,
        "bc_inj": Lbc,
        "bc_tip": Ltip,
        "anchor": La,
        "mono": Lmono,
        "total": total,
    }


# =============================================================================
# XPU smoke
# =============================================================================

def xpu_smoke_test(device):
    print("\nXPU COMPRESSIBLE LSTM SMOKE TEST")

    test = nn.LSTM(
        input_size=12,
        hidden_size=64,
        num_layers=2,
        batch_first=True,
    ).to(device)

    x = torch.randn(
        8,
        64,
        12,
        device=device,
        requires_grad=True,
    )

    y, _ = test(x)
    loss = (y ** 2).mean()
    loss.backward()
    sync_xpu()

    passed = (
        y.device.type == "xpu"
        and x.grad is not None
        and torch.isfinite(y).all().item()
        and torch.isfinite(x.grad).all().item()
    )

    print("  output device   :", y.device)
    print("  forward/backward:", "PASS" if passed else "FAIL")

    del test, x, y, loss

    if hasattr(torch.xpu, "empty_cache"):
        torch.xpu.empty_cache()

    if not passed:
        raise RuntimeError("XPU compressible LSTM smoke test failed.")


# =============================================================================
# Training
# =============================================================================

def train_xpu(
    model,
    arrays,
    device,
    microbatch,
    epochs,
):
    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    N = len(xi_all)

    rng = np.random.default_rng(SEED)
    idx = np.arange(N)
    rng.shuffle(idx)

    n_train = int(0.8 * N)
    train_idx = idx[:n_train]
    holdout_idx = idx[n_train:]

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LR,
    )

    history = {
        "epoch": [],
        "data": [],
        "physics": [],
        "bc_inj": [],
        "bc_tip": [],
        "anchor": [],
        "mono": [],
        "total": [],
        "epoch_seconds": [],
    }

    print("\nXPU TRAINING")
    print("  device             :", device)
    print("  train profiles     :", len(train_idx))
    print("  holdout profiles   :", len(holdout_idx))
    print("  logical batch      :", LOGICAL_BATCH)
    print("  XPU microbatch     :", microbatch)
    print(
        "  optimizer updates/epoch:",
        math.ceil(len(train_idx) / LOGICAL_BATCH),
    )
    print("  epochs             :", epochs)
    print("  mixed precision    : OFF")

    global_t0 = time.time()

    for epoch in range(1, epochs + 1):
        t0 = time.time()

        erng = np.random.default_rng(
            SEED + epoch
        )
        order = train_idx.copy()
        erng.shuffle(order)

        sums = {
            "data": 0.0,
            "physics": 0.0,
            "bc_inj": 0.0,
            "bc_tip": 0.0,
            "anchor": 0.0,
            "mono": 0.0,
            "total": 0.0,
        }
        count = 0

        for b0 in range(
            0,
            len(order),
            LOGICAL_BATCH,
        ):
            logical_idx = order[
                b0:b0 + LOGICAL_BATCH
            ]
            logical_n = len(logical_idx)

            optimizer.zero_grad(
                set_to_none=True
            )

            for m0 in range(
                0,
                logical_n,
                microbatch,
            ):
                ids = logical_idx[
                    m0:m0 + microbatch
                ]
                m = len(ids)

                xi = torch.from_numpy(
                    xi_all[ids]
                ).to(device)

                Sw = torch.from_numpy(
                    Sw_all[ids]
                ).to(device)

                p11 = torch.from_numpy(
                    p11_all[ids]
                ).to(device)

                tD = torch.from_numpy(
                    tD_all[ids]
                ).to(device)

                ai = torch.from_numpy(
                    ai_all[ids]
                ).to(device)

                at = torch.from_numpy(
                    at_all[ids]
                ).to(device)

                _, parts = total_losses(
                    model,
                    xi,
                    Sw,
                    p11,
                    tD,
                    ai,
                    at,
                )

                scale = (
                    float(m)
                    / float(logical_n)
                )

                (
                    parts["total"] * scale
                ).backward()

                for k in sums:
                    sums[k] += (
                        float(
                            parts[k]
                            .detach()
                            .cpu()
                        ) * m
                    )

                count += m

                del xi, Sw, p11, tD, ai, at, parts

            optimizer.step()

        sync_xpu()

        n = max(count, 1)
        sec = time.time() - t0

        history["epoch"].append(epoch)

        for k in sums:
            history[k].append(
                sums[k] / n
            )

        history["epoch_seconds"].append(sec)

        if (
            epoch == 1
            or epoch % 10 == 0
            or epoch == epochs
        ):
            print(
                f"[XPU-COMP] Epoch {epoch:04d}/{epochs} "
                f"| Data {history['data'][-1]:.3e} "
                f"| Phys {history['physics'][-1]:.3e} "
                f"| BC {history['bc_inj'][-1]:.3e} "
                f"| Tip {history['bc_tip'][-1]:.3e} "
                f"| Anchor {history['anchor'][-1]:.3e} "
                f"| Mono {history['mono'][-1]:.3e} "
                f"| {sec:.2f}s/epoch "
                f"| total {time.time()-global_t0:.1f}s"
            )

    return history, train_idx, holdout_idx


# =============================================================================
# Evaluation
# =============================================================================

@torch.no_grad()
def holdout_metrics(
    model,
    arrays,
    holdout_idx,
    device,
):
    xi_all, Sw_all, p11_all, _, _, _ = arrays

    total_sq = 0.0
    total_abs = 0.0
    total_n = 0
    max_abs = 0.0
    lower = 0
    upper = 0
    finite = True

    batch = 1024

    for i0 in range(
        0,
        len(holdout_idx),
        batch,
    ):
        ids = holdout_idx[
            i0:i0 + batch
        ]

        xi = torch.from_numpy(
            xi_all[ids]
        ).to(device)

        p11 = torch.from_numpy(
            p11_all[ids]
        ).to(device)

        pred = model(
            xi,
            p11,
        ).cpu().numpy()

        truth = Sw_all[ids]
        err = pred - truth
        ae = np.abs(err)

        finite = (
            finite
            and np.isfinite(pred).all()
            and np.isfinite(err).all()
        )

        total_sq += float(
            np.sum(err ** 2)
        )
        total_abs += float(
            np.sum(ae)
        )
        total_n += int(err.size)
        max_abs = max(
            max_abs,
            float(np.max(ae)),
        )

        swc = p11_all[
            ids, 2
        ].reshape(-1, 1, 1)

        sor = p11_all[
            ids, 3
        ].reshape(-1, 1, 1)

        lower += int(
            np.sum(pred < swc - 1e-7)
        )
        upper += int(
            np.sum(
                pred > (1.0 - sor) + 1e-7
            )
        )

    mse = total_sq / max(total_n, 1)

    return {
        "mse": mse,
        "rmse": math.sqrt(mse),
        "mae": total_abs / max(total_n, 1),
        "max_abs_error": max_abs,
        "finite_predictions": bool(finite),
        "lower_bound_violations": lower,
        "upper_bound_violations": upper,
        "bounds_pass": lower == 0 and upper == 0,
        "n_scalar_predictions": total_n,
    }


def make_case(
    no,
    nw,
    swc,
    sor,
    mu_w,
    mu_o,
    phi,
):
    p = dict(BASE_P)
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
def predict_against_ref(
    model,
    p_case,
    t_days,
    Nc,
    device,
):
    # Conditioner pipeline uses NX_TRAIN, as frozen source.
    fan = build_fan_profiles_godunov(
        [t_days],
        p_case,
        Nc=Nc,
        n_fan=64,
        nx=NX_TRAIN,
    )

    if not fan:
        raise ValueError(
            f"No front at {t_days} d, Nc={Nc}"
        )

    fan = fan[0]

    xi = fan["xi"]
    tD = fan["t_D"]
    xD_star = fan["xD_star"]
    Sw_star = fan["Sw_star"]

    p11 = np.array([[
        p_case["no"],
        p_case["nw"],
        p_case["swc"],
        p_case["sor"],
        p_case["mu_w"],
        p_case["mu_o"],
        p_case["phi"],
        tD,
        xD_star,
        Sw_star,
        Nc,
    ]], dtype=np.float32)

    x = torch.from_numpy(
        xi.reshape(1, -1, 1)
    ).to(device)

    p = torch.from_numpy(
        p11
    ).to(device)

    Sw_fan = model(
        x,
        p,
    ).cpu().numpy().squeeze()

    xD_pred = np.concatenate([
        xi * xD_star,
        [xD_star, 1.0],
    ])

    Sw_pred = np.concatenate([
        Sw_fan,
        [p_case["swc"], p_case["swc"]],
    ])

    # Fine-grid authority
    xD_true, snaps = godunov_compressible_snapshots(
        p_case,
        Nc,
        [t_days],
        nx=NX_REF,
    )

    Sw_true = snaps[0]

    xD_star_true = godunov_front_from_profile(
        xD_true,
        Sw_true,
        Sw_star,
        p_case["swc"],
    )

    return {
        "xD_true": xD_true,
        "Sw_true": Sw_true,
        "xD_pred": xD_pred,
        "Sw_pred": Sw_pred,
        "t_days": float(t_days),
        "t_D": float(tD),
        "Nc": float(Nc),
        "xD_star_true": float(xD_star_true),
    }


def evaluate_case(
    model,
    p_case,
    Nc,
    device,
    n_times=15,
):
    t_bt = breakthrough_time_days(
        p_case,
        Nc=Nc,
    )

    times = np.linspace(
        100.0,
        0.95 * t_bt,
        n_times,
    )

    rows = []
    residuals = []
    truths = []
    preds = []

    common_x = np.linspace(
        0.0,
        1.0,
        200,
    )

    for t in times:
        r = predict_against_ref(
            model,
            p_case,
            float(t),
            Nc,
            device,
        )

        pred_interp = np.interp(
            r["xD_true"],
            r["xD_pred"],
            r["Sw_pred"],
        )

        err = pred_interp - r["Sw_true"]

        rows.append({
            "t_days": r["t_days"],
            "t_D": r["t_D"],
            "Nc": r["Nc"],
            "xD_star_true": r["xD_star_true"],
            "mse": float(
                np.mean(err ** 2)
            ),
            "mae": float(
                np.mean(np.abs(err))
            ),
            "max_abs_err": float(
                np.max(np.abs(err))
            ),
        })

        true_c = np.interp(
            common_x,
            r["xD_true"],
            r["Sw_true"],
        )

        pred_c = np.interp(
            common_x,
            r["xD_pred"],
            r["Sw_pred"],
        )

        residuals.append(
            pred_c - true_c
        )
        truths.append(true_c)
        preds.append(pred_c)

    residuals = np.asarray(residuals)
    truths = np.asarray(truths)
    preds = np.asarray(preds)

    rf = residuals.ravel()
    tf = truths.ravel()
    pf = preds.ravel()

    ss_res = float(
        np.sum((tf - pf) ** 2)
    )
    ss_tot = float(
        np.sum((tf - np.mean(tf)) ** 2)
    )

    r2 = 1.0 - ss_res / max(
        ss_tot,
        EPS,
    )

    return {
        "Nc": float(Nc),
        "breakthrough_time_days": float(t_bt),
        "rows": rows,
        "diagnostics": {
            "mean_residual": float(np.mean(rf)),
            "std_residual": float(np.std(rf)),
            "max_abs_residual": float(
                np.max(np.abs(rf))
            ),
            "r_squared": float(r2),
            "n_evaluation_points": int(len(rf)),
        },
    }


def nc_accuracy_sweep(
    model,
    p_case,
    device,
):
    out = {}

    for Nc in (
        0.0,
        0.05,
        0.10,
        0.20,
        0.30,
    ):
        t_bt = breakthrough_time_days(
            p_case,
            Nc=Nc,
        )

        errs = []

        for t in np.linspace(
            100.0,
            0.95 * t_bt,
            8,
        ):
            r = predict_against_ref(
                model,
                p_case,
                float(t),
                Nc,
                device,
            )

            pred = np.interp(
                r["xD_true"],
                r["xD_pred"],
                r["Sw_pred"],
            )

            errs.append(
                np.abs(
                    pred - r["Sw_true"]
                )
            )

        e = np.concatenate(errs)

        out[f"{Nc:.2f}"] = {
            "mae": float(e.mean()),
            "max_abs_error": float(e.max()),
        }

    return out


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--microbatch",
        type=int,
        default=DEFAULT_MICROBATCH,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, max(1, os.cpu_count() or 1)),
        help="CPU workers for independent Godunov teacher cases.",
    )

    parser.add_argument(
        "--force-rebuild-dataset",
        action="store_true",
    )

    parser.add_argument(
        "--smoke-epochs",
        type=int,
        default=0,
        help="Engineering smoke only; 0 means full 400-epoch certifiable run.",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("PAD-Stream V16E-1B2-XPU")
    print("Final Compressible BL PI-RNN Native-Coordinate XPU Reproduction")
    print("=" * 80)
    print("Experiment:", EXPERIMENT_ID)
    print()

    if SUMMARY.exists():
        raise RuntimeError(
            "Certified E1B2-XPU summary exists; refusing overwrite."
        )

    # -------------------------------------------------------------------------
    # Upstream authority
    # -------------------------------------------------------------------------

    gates = {
        "B1_R1_source_SHA_exact":
            exact_sha(B1_R1_SOURCE, B1_R1_SOURCE_SHA),
        "B1_checkpoint_SHA_exact":
            exact_sha(B1_CHECKPOINT, B1_CHECKPOINT_SHA),
        "B1_metrics_SHA_exact":
            exact_sha(B1_METRICS, B1_METRICS_SHA),
        "B1_repair_SHA_exact":
            exact_sha(B1_REPAIR, B1_REPAIR_SHA),
        "B1_manifest_SHA_exact":
            exact_sha(B1_MANIFEST, B1_MANIFEST_SHA),
        "B1_summary_SHA_exact":
            exact_sha(B1_SUMMARY, B1_SUMMARY_SHA),
        "Stage2_source_SHA_exact":
            exact_sha(SOURCE, SOURCE_SHA),
    }

    b1_summary = (
        read_json(B1_SUMMARY)
        if B1_SUMMARY.exists()
        else {}
    )

    gates.update({
        "B1_status_exact":
            b1_summary.get("status")
            == EXPECTED_B1_STATUS,
        "B1_next_authorizes_COMP_XPU":
            isinstance(
                b1_summary.get("next_milestone"),
                str,
            )
            and "Compressible" in b1_summary["next_milestone"],
        "B1_training_not_repeated_in_R1":
            b1_summary.get("training_repeated_in_R1")
            is False,
        "B1_weights_not_modified_in_R1":
            b1_summary.get("weights_modified_in_R1")
            is False,
    })

    print("UPSTREAM CERTIFICATION GATES")
    for k, v in gates.items():
        print("[PASS]" if v else "[FAIL]", k)

    if not all(gates.values()):
        raise RuntimeError(
            "V16E-1B2-XPU blocked by upstream authority mismatch."
        )

    # -------------------------------------------------------------------------
    # Prospective port protocol
    # -------------------------------------------------------------------------

    protocol = {
        "milestone": "V16E-1B2-XPU",
        "experiment_id": EXPERIMENT_ID,
        "classification":
            "FRAMEWORK_EQUIVALENT_ACCELERATION_PORT",

        "source": {
            "path": rel(SOURCE),
            "sha256": SOURCE_SHA,
        },

        "teacher": {
            "type":
                "conservative compressible finite-volume Godunov",
            "velocity":
                "u(x_D)=u_inj*exp(Nc*x_D)",
            "NX_TRAIN": NX_TRAIN,
            "NX_REF": NX_REF,
            "n_fan": 64,
        },

        "conditioning_order": CONDITIONING,
        "param_dim": PARAM_DIM,

        "architecture":
            "xi+p11 -> LSTM64 -> LSTM64 -> Dense1 -> sigmoid range map",

        "physics_residual":
            "R=y(xi*xD_star;Nc)-tD*dfw/dSw; "
            "y=-expm1(-Nc*x)/Nc with exact Nc=0 limit",

        "dataset": {
            "Nc_grid": NC_VALS.tolist(),
            "max_seeded_case_Nc_combinations": 2400,
            "seed": SEED,
            "num_times": 6,
            "t_min_days": 100.0,
            "horizon": "0.95*t_BT",
            "parallel_cpu_scheduling_allowed": True,
            "parallelization_changes_physics": False,
        },

        "training": {
            "optimizer": "Adam",
            "learning_rate": LR,
            "epochs": EPOCHS,
            "logical_batch": LOGICAL_BATCH,
            "default_XPU_microbatch": DEFAULT_MICROBATCH,
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

        "evaluation": {
            "holdout_semantics":
                "source-native reproduction holdout; NOT OOD",
            "fine_grid_teacher_NX": NX_REF,
            "Stage1_nesting_Nc0": True,
            "Nc_accuracy_sweep":
                [0.0, 0.05, 0.10, 0.20, 0.30],
            "numeric_threshold_invented": False,
        },

        "framework_difference":
            "PyTorch/XPU is not bitwise TensorFlow. "
            "Teacher, conditioning, physics, architecture topology, losses, "
            "logical batch and evaluation semantics are frozen.",
    }

    PORT_PROTOCOL.write_text(
        json.dumps(protocol, indent=2),
        encoding="utf-8",
    )

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    print("\nRUNTIME")
    print("  PyTorch:", torch.__version__)
    print("  XPU available:", torch.xpu.is_available())
    print(
        "  XPU count:",
        torch.xpu.device_count()
        if torch.xpu.is_available()
        else 0,
    )

    if not torch.xpu.is_available():
        raise RuntimeError("Intel XPU unavailable.")

    device = torch.device("xpu")
    torch.manual_seed(SEED)

    xpu_smoke_test(device)

    # -------------------------------------------------------------------------
    # Dataset
    # -------------------------------------------------------------------------

    arrays = build_or_load_dataset(
        force=args.force_rebuild_dataset,
        workers=max(1, args.workers),
    )

    xi_all, Sw_all, p11_all, tD_all, ai_all, at_all = arrays

    gates.update({
        "dataset_sequence_length_64":
            xi_all.shape[1:] == (64, 1),
        "dataset_param_dim_11":
            p11_all.shape[1] == 11,
        "dataset_Nc_values_subset_of_frozen_grid":
            set(
                np.round(
                    np.unique(p11_all[:, 10]),
                    5,
                ).tolist()
            ).issubset(
                set(
                    np.round(
                        NC_VALS,
                        5,
                    ).tolist()
                )
            ),
        "dataset_SHA_meta_exact":
            read_json(DATASET_META).get("dataset_sha256")
            == sha256(DATASET),
        "dataset_parallel_order_preserved":
            read_json(DATASET_META).get(
                "parallel_output_order_preserved"
            ) is True,
    })

    if not all(gates.values()):
        raise RuntimeError("Stage-2 dataset gate failed.")

    # -------------------------------------------------------------------------
    # Model / config
    # -------------------------------------------------------------------------

    torch.manual_seed(SEED)
    model = CompressiblePIRNNXPU().to(device)

    gates["model_parameters_on_XPU"] = (
        {p.device.type for p in model.parameters()}
        == {"xpu"}
    )

    full_run = args.smoke_epochs == 0
    epochs = (
        EPOCHS
        if full_run
        else int(args.smoke_epochs)
    )

    config = {
        "experiment_id": EXPERIMENT_ID,
        "framework": "PyTorch XPU",
        "pytorch_version": torch.__version__,
        "device": str(device),

        "source_sha256": SOURCE_SHA,
        "framework_port_protocol_sha256":
            sha256(PORT_PROTOCOL),

        "condition_on": CONDITIONING,
        "param_dim": PARAM_DIM,
        "hidden": HIDDEN,
        "layers": LAYERS,

        "seed": SEED,
        "optimizer": "Adam",
        "learning_rate": LR,
        "logical_batch_size": LOGICAL_BATCH,
        "microbatch": args.microbatch,
        "epochs_requested": epochs,
        "full_certification_run": full_run,
        "mixed_precision": False,

        "teacher": {
            "NX_TRAIN": NX_TRAIN,
            "NX_REF": NX_REF,
            "Nc_vals": NC_VALS.tolist(),
            "max_cases": 2400,
        },

        "dataset": {
            "path": rel(DATASET),
            "sha256": sha256(DATASET),
        },
    }

    if full_run:
        CONFIG.write_text(
            json.dumps(config, indent=2),
            encoding="utf-8",
        )

    # -------------------------------------------------------------------------
    # Train
    # -------------------------------------------------------------------------

    history, train_idx, holdout_idx = train_xpu(
        model=model,
        arrays=arrays,
        device=device,
        microbatch=args.microbatch,
        epochs=epochs,
    )

    if not full_run:
        torch.save(
            {
                "experiment_id":
                    EXPERIMENT_ID + "-SMOKE",
                "model_state_dict":
                    model.state_dict(),
                "source_sha256":
                    SOURCE_SHA,
                "epochs":
                    epochs,
            },
            SMOKE_CHECKPOINT,
        )

        print("\nSMOKE RUN COMPLETE")
        print("This is NOT a certifiable V16E reproduction.")
        print(
            "Smoke checkpoint:",
            SMOKE_CHECKPOINT,
        )
        print(
            "Smoke SHA-256:",
            sha256(SMOKE_CHECKPOINT),
        )
        return

    HISTORY.write_text(
        json.dumps(
            jsonable(history),
            indent=2,
        ),
        encoding="utf-8",
    )

    torch.save(
        {
            "experiment_id": EXPERIMENT_ID,
            "source_sha256": SOURCE_SHA,
            "framework": "PyTorch XPU",
            "pytorch_version": torch.__version__,
            "conditioning": CONDITIONING,
            "param_dim": PARAM_DIM,
            "hidden": HIDDEN,
            "layers": LAYERS,
            "model_state_dict":
                model.state_dict(),
        },
        CHECKPOINT,
    )

    # -------------------------------------------------------------------------
    # Critical Intel XPU inference mode
    # -------------------------------------------------------------------------

    model.eval()

    gates.update({
        "full_400_epochs_completed":
            len(history["epoch"]) == 400,
        "checkpoint_written":
            CHECKPOINT.exists()
            and CHECKPOINT.stat().st_size > 0,
        "history_written":
            HISTORY.exists()
            and HISTORY.stat().st_size > 0,
        "config_written":
            CONFIG.exists()
            and CONFIG.stat().st_size > 0,
        "model_eval_mode_before_inference":
            model.training is False,
    })

    # -------------------------------------------------------------------------
    # Evaluation
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

    p1 = make_case(
        no=2.0,
        nw=2.0,
        swc=0.20,
        sor=0.20,
        mu_w=0.5,
        mu_o=0.7,
        phi=0.20,
    )

    p2 = make_case(
        no=3.0,
        nw=2.0,
        swc=0.15,
        sor=0.25,
        mu_w=6.0,
        mu_o=0.9,
        phi=0.25,
    )

    print("\nSOURCE CASE DIAGNOSTICS")

    cases = {
        "case1_nc0_stage1_nesting":
            evaluate_case(
                model,
                p1,
                0.0,
                device,
            ),
        "case1_nc01":
            evaluate_case(
                model,
                p1,
                0.10,
                device,
            ),
        "case2_nc0_stage1_nesting":
            evaluate_case(
                model,
                p2,
                0.0,
                device,
            ),
        "case2_nc02":
            evaluate_case(
                model,
                p2,
                0.20,
                device,
            ),
    }

    for name, case in cases.items():
        print(
            f"  {name:<30} "
            f"R2={case['diagnostics']['r_squared']:.8f} "
            f"max_res={case['diagnostics']['max_abs_residual']:.5e}"
        )

    print("\nNc ACCURACY SWEEP — CASE 1")
    sweep = nc_accuracy_sweep(
        model,
        p1,
        device,
    )

    for nc, vals in sweep.items():
        print(
            f"  Nc={nc} "
            f"MAE={vals['mae']:.5e} "
            f"max={vals['max_abs_error']:.5e}"
        )

    def case_finite(case):
        return (
            len(case["rows"]) == 15
            and all(
                finite_number(r["mse"])
                and finite_number(r["mae"])
                and finite_number(r["max_abs_err"])
                for r in case["rows"]
            )
            and finite_number(
                case["diagnostics"]["r_squared"]
            )
            and finite_number(
                case["diagnostics"]["max_abs_residual"]
            )
        )

    gates.update({
        "holdout_predictions_finite":
            holdout["finite_predictions"],
        "holdout_bounds_pass":
            holdout["bounds_pass"],
        "holdout_metrics_finite":
            all(
                finite_number(holdout[k])
                for k in (
                    "mse",
                    "rmse",
                    "mae",
                    "max_abs_error",
                )
            ),

        "all_four_source_cases_finite":
            all(
                case_finite(c)
                for c in cases.values()
            ),

        "Nc_sweep_all_finite":
            all(
                finite_number(v["mae"])
                and finite_number(
                    v["max_abs_error"]
                )
                for v in sweep.values()
            ),

        "Stage1_nesting_Nc0_evaluated":
            "case1_nc0_stage1_nesting"
            in cases
            and "case2_nc0_stage1_nesting"
            in cases,

        "no_TOF": True,
        "no_OOD": True,
        "no_mixed_precision": True,
        "no_numeric_threshold_invented": True,
    })

    metrics = {
        "milestone": "V16E-1B2-XPU",
        "experiment_id": EXPERIMENT_ID,
        "classification":
            "FRAMEWORK_EQUIVALENT_NATIVE_COORDINATE_XPU_REPRODUCTION",

        "dataset": {
            "path": rel(DATASET),
            "sha256": sha256(DATASET),
            "profile_count": len(xi_all),
            "train_count": len(train_idx),
            "holdout_count": len(holdout_idx),
            "xi_shape": list(xi_all.shape),
            "p11_shape": list(p11_all.shape),
        },

        "training": {
            "epochs_completed":
                len(history["epoch"]),
            "microbatch":
                args.microbatch,
            "logical_batch":
                LOGICAL_BATCH,
            "final_losses": {
                k: history[k][-1]
                for k in (
                    "data",
                    "physics",
                    "bc_inj",
                    "bc_tip",
                    "anchor",
                    "mono",
                    "total",
                )
            },
            "mean_epoch_seconds":
                float(
                    np.mean(
                        history["epoch_seconds"]
                    )
                ),
        },

        "holdout": holdout,
        "source_cases": cases,
        "Nc_accuracy_sweep_case1": sweep,

        "threshold_policy":
            "No numerical acceptance threshold invented or applied.",
    }

    METRICS.write_text(
        json.dumps(
            jsonable(metrics),
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "classification":
            "FRAMEWORK_EQUIVALENT_XPU_REPRODUCTION",

        "source": {
            "path": rel(SOURCE),
            "sha256": SOURCE_SHA,
        },

        "upstream_E1B1_XPU_R1": {
            "summary_sha256":
                B1_SUMMARY_SHA,
            "checkpoint_sha256":
                B1_CHECKPOINT_SHA,
        },

        "framework": {
            "name": "PyTorch XPU",
            "version": torch.__version__,
            "model_eval_used_for_inference":
                True,
            "bitwise_TensorFlow_equivalence_claimed":
                False,
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
            "OOD_claim": False,
            "TOF": False,
            "mixed_precision": False,
            "PhysicsNeMo": False,
            "numeric_threshold_invented": False,
            "EXP_CS1_retraining": False,
            "geology0029_reopening": False,
        },
    }

    MANIFEST.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    gates.update({
        "metrics_written":
            METRICS.exists()
            and METRICS.stat().st_size > 0,
        "manifest_written":
            MANIFEST.exists()
            and MANIFEST.stat().st_size > 0,
        "manifest_checkpoint_SHA_exact":
            read_json(MANIFEST)[
                "artifacts"
            ]["checkpoint"]["sha256"]
            == sha256(CHECKPOINT),
        "manifest_metrics_SHA_exact":
            read_json(MANIFEST)[
                "artifacts"
            ]["metrics"]["sha256"]
            == sha256(METRICS),
    })

    ok = all(bool(v) for v in gates.values())

    status = (
        "V16E1B2_XPU_FINAL_COMPRESSIBLE_BL_PI_RNN_"
        "FRAMEWORK_EQUIVALENT_NATIVE_COORDINATE_REPRODUCTION_COMPLETE_"
        "CONSERVATIVE_GODUNOV_TEACHER_BOUND_"
        "NC_CONDITIONING_AND_TRAVEL_TIME_RESIDUAL_CERTIFIED_"
        "INTEL_XPU_EXECUTION_CONFIRMED_NEW_CHECKPOINT_SHA_BOUND_"
        "SOURCE_NATIVE_HOLDOUT_CASE_DIAGNOSTICS_AND_NC_SWEEP_FINITE_"
        "SATURATION_BOUNDS_PASS_STAGE1_NC0_NESTING_EVALUATED_"
        "NO_OOD_NO_TOF_"
        "V16E1B3_XPU_CAPILLARY_PORT_AUTHORIZED"
        if ok else
        "V16E1B2_XPU_REPRODUCTION_COMPLETED_WITH_GATE_FAILURE"
    )

    summary = {
        "milestone": "V16E-1B2-XPU",
        "experiment_id": EXPERIMENT_ID,
        "status": status,

        "source_sha256": SOURCE_SHA,
        "dataset_sha256": sha256(DATASET),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "config_sha256": sha256(CONFIG),
        "port_protocol_sha256": sha256(PORT_PROTOCOL),
        "history_sha256": sha256(HISTORY),
        "metrics_sha256": sha256(METRICS),
        "manifest_sha256": sha256(MANIFEST),

        "holdout_mse": holdout["mse"],
        "holdout_rmse": holdout["rmse"],
        "holdout_mae": holdout["mae"],
        "holdout_max_abs_error": holdout["max_abs_error"],

        "next_milestone": (
            "V16E-1B3-XPU — Final Capillary BL PI-RNN "
            "framework-equivalent native-coordinate XPU port/reproduction"
            if ok else
            "V16E-1B2-XPU-R1 — diagnose failed gate"
        ),

        "gates": {
            k: bool(v)
            for k, v in gates.items()
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
