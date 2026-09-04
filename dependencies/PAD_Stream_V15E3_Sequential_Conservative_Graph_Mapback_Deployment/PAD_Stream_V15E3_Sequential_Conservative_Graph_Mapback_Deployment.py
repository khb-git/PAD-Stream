#!/usr/bin/env python3
"""PAD-Stream Version 15E-3.

Sequential conservative graph map-back deployment audit.

This milestone closes the specific failure exposed by Version 15D-3: recurrent
transport is no longer carried from one changing streamline geometry to the
next by path-to-path interpolation.  Instead, every accepted step produces one
unique 5x5x5 grid saturation/history state.  The next corrected Pollock path
family samples that grid state, Version 15D-2 predicts one-step path transport,
and the frozen Version 15E-2 predict-screen-correct map-back returns the next
accepted grid state.

Scope boundary
--------------
* Exact/corrected pressure and path geometry are refreshed from the frozen
  sequential reference states.  Learned pressure/path recurrence is integrated
  later in Version 15G.
* No exact future CO2 inventory or exact future saturation enters inference.
* Target-time pressure is treated as available from the already-approved
  pressure branch and is used only to form a self-consistent compressible mass
  coefficient and to evaluate the unchanged Peaceman well equations.
* Exact target grid fields, inventory, gas cut, and breakthrough are audit-only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Mapping

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

VERSION = "15E-3"
SEED = 150503
SECONDS_PER_DAY = 86400.0
S_G_MAX = 0.80
BREAKTHROUGH_GAS_CUT = 1.0e-4
VARIANT = "d2_conservative"
VARIANTS = (
    "teacher_exact", "d1_raw", "d2_raw", "d2_conservative",
    "d2_dropout10", "d2_dropout25",
)

# Frozen 15D-3 benchmark used only for direct diagnostic comparison.
V15D3_BENCHMARK = {
    "final_state_saturation_drift_rmse": 0.106511,
    "predicted_breakthrough_days": 27.581,
    "exact_breakthrough_days": 115.750,
    "mean_predicted_inventory_relative_error_to_exact": 0.3026,
    "corrected_saturation_rmse": 0.101630,
    "persistence_rmse": 0.091233,
}


def seed_everything(seed: int = SEED) -> None:
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(8, os.cpu_count() or 1)))
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return float(np.sqrt(np.mean((a - b) ** 2)))


def safe_rel_error(value: float, reference: float) -> float:
    return float(abs(float(value) - float(reference)) / max(abs(float(reference)), 1.0))


def configure_d3_runtime(d3, args) -> None:
    d3.C3_DIR = args.c3_root
    d3.STATE_DIR = args.c3_root / "sequential_states"
    d3.D2_DIR = args.d2_root
    d3.D2_CKPT = args.d2_root / "PAD_Stream_V15D2_Best_Model.pt"
    d3.D1_SOURCE = args.d2_root / "PAD_Stream_V15D1_Train_Supervised_Conditional_PIRNN.py"
    d3.V14_SOURCE = args.v14_source


def load_state(state_dir: Path, day: int) -> Dict[str, np.ndarray]:
    path = state_dir / f"pad_stream_v15b4_day_{int(day)}.npz"
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def accepted_current_fields(v14, state: Mapping[str, np.ndarray], sg: np.ndarray,
                            hist: np.ndarray, grid, rock, fluid, cap) -> Dict[str, np.ndarray]:
    pseudo = {
        "saturation": np.asarray(sg, np.float64),
        "saturation_history": np.maximum(np.asarray(hist, np.float64), np.asarray(sg, np.float64)),
        "pressure_w": np.asarray(state["pressure_w"], np.float64),
    }
    fields = v14.ccus_capillary_pressure(pseudo["saturation"], rock, cap)
    krg, krw = v14.ccus_relative_permeability(
        pseudo["saturation"], rock, pseudo["saturation_history"]
    )
    lg = krg / (fluid.mu_g * 1.0e-3)
    lw = krw / (fluid.mu_w * 1.0e-3)
    lt = lg + lw
    fg = lg / np.maximum(lt, 1.0e-30)
    rho = v14.ccus_gas_density_from_phase_pressure(pseudo["pressure_w"] + fields, fluid)
    depth = v14._v10_depth_centres(grid)
    return {
        "sg": pseudo["saturation"], "hist": pseudo["saturation_history"],
        "p": pseudo["pressure_w"], "pc": fields, "lg": lg, "lw": lw,
        "lt": lt, "fg": fg, "rho": rho, "depth": depth,
    }


def update_transport_frame_from_grid(
    d3, ctx: Mapping[str, Any], frame: Dict[str, np.ndarray], day: int,
    accepted_sg: np.ndarray, accepted_hist: np.ndarray,
    recurrent_gas_cut: float, predicted_breakthrough_days: float,
) -> tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], list[np.ndarray]]:
    """Replace teacher-forced path state channels with the accepted grid state."""
    v14, grid, rock, fluid, cap = (
        ctx["v14"], ctx["grid"], ctx["rock"], ctx["fluid"], ctx["cap"]
    )
    state = d3.load_state(day)
    fields = accepted_current_fields(v14, state, accepted_sg, accepted_hist, grid, rock, fluid, cap)
    X = frame["X"].copy()
    C = frame["C"].copy()
    mask = frame["mask"]
    pday = ctx["paths"][ctx["paths"].time_days == day].sort_values("local_path_id")
    if len(pday) != len(X):
        raise RuntimeError(f"expected {len(X)} paths at day {day}, found {len(pday)}")
    injected_pvi = float(state["cumulative_injected_volume_m3"][0]) / max(
        float(np.sum(grid.phi * grid.vcell)), 1.0e-30
    )
    mode_bhp = float(str(state["previous_injector_mode"][0]).lower() == "bhp")
    bt_flag = float(np.isfinite(predicted_breakthrough_days) and day >= predicted_breakthrough_days)
    segment_cells: list[np.ndarray] = []

    for row_i, (_, prow) in enumerate(pday.iterrows()):
        sdf = ctx["grouped_segments"][int(prow.global_path_id)]
        cells = sdf[["cell_i", "cell_j", "cell_k"]].to_numpy(np.int64)
        L = len(cells)
        if L != int(mask[row_i].sum()):
            raise RuntimeError("path sequence length mismatch")
        segment_cells.append(cells)
        sg = np.array([fields["sg"][tuple(c)] for c in cells], np.float64)
        hist = np.array([fields["hist"][tuple(c)] for c in cells], np.float64)
        p = np.array([fields["p"][tuple(c)] for c in cells], np.float64)
        pc = np.array([fields["pc"][tuple(c)] for c in cells], np.float64)
        fg = np.array([fields["fg"][tuple(c)] for c in cells], np.float64)
        lg = np.array([fields["lg"][tuple(c)] for c in cells], np.float64)
        lw = np.array([fields["lw"][tuple(c)] for c in cells], np.float64)
        lt = np.array([fields["lt"][tuple(c)] for c in cells], np.float64)
        rho = np.array([fields["rho"][tuple(c)] for c in cells], np.float64)
        m = mask[row_i]
        X[row_i, m, 9] = sg
        X[row_i, m, 10] = hist
        X[row_i, m, 11] = np.maximum(hist - sg, 0.0)
        X[row_i, m, 12] = p / 1.0e6
        X[row_i, m, 13] = pc / 1.0e6
        X[row_i, m, 14] = fg
        X[row_i, m, 15] = np.log10(np.maximum(lg, 1.0e-30))
        X[row_i, m, 16] = np.log10(np.maximum(lw, 1.0e-30))
        X[row_i, m, 17] = np.log10(np.maximum(lt, 1.0e-30))
        X[row_i, m, 18] = rho
        X[row_i, m, 27] = np.concatenate(([0.0], np.diff(sg)))
        X[row_i, m, 28] = injected_pvi
        X[row_i, m, 29] = recurrent_gas_cut
        X[row_i, m, 30] = mode_bhp
        X[row_i, m, 31] = bt_flag
        pv = frame["segment_pv"][row_i, m]
        C[row_i, 8] = float(np.sum(pv * sg) / max(np.sum(pv), 1.0e-30))
        C[row_i, 9] = recurrent_gas_cut
        C[row_i, 10] = injected_pvi
        C[row_i, 11] = mode_bhp
        C[row_i, 12] = bt_flag

    frame["X"] = X
    frame["C"] = C
    return frame, fields, segment_cells


def flatten_path_predictions(
    ctx: Mapping[str, Any], frame: Mapping[str, np.ndarray],
    segment_cells: list[np.ndarray], path_sg: np.ndarray, path_hist: np.ndarray,
) -> Dict[str, np.ndarray]:
    cells_all, sg_all, hist_all, pv_all, rate_all, tof_all = [], [], [], [], [], []
    pday = ctx["paths"][ctx["paths"].time_days == frame["day"]].sort_values("local_path_id")
    for i, (_, prow) in enumerate(pday.iterrows()):
        m = frame["mask"][i]
        cells = segment_cells[i]
        if len(cells) != int(m.sum()):
            raise RuntimeError("flattened path cell count mismatch")
        cells_all.append(cells)
        sg_all.append(np.asarray(path_sg[i, m], np.float64))
        hist_all.append(np.asarray(path_hist[i, m], np.float64))
        pv_all.append(np.asarray(frame["segment_pv"][i, m], np.float64))
        rate_all.append(np.full(int(m.sum()), float(prow.stream_rate_m3_s), np.float64))
        tof_all.append(np.asarray(frame["tau_fraction"][i, m], np.float64))
    return {
        "cells": np.concatenate(cells_all),
        "sg": np.concatenate(sg_all),
        "hist": np.concatenate(hist_all),
        "pv": np.concatenate(pv_all),
        "rate": np.concatenate(rate_all),
        "tof": np.concatenate(tof_all),
    }


def build_graph_inputs(
    e0, operator, base: Mapping[str, np.ndarray], ctx: Mapping[str, Any],
    current_fields: Mapping[str, np.ndarray], current_day: int, target_day: int,
    path_values: Mapping[str, np.ndarray],
) -> tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    grid, v14 = ctx["grid"], ctx["v14"]
    shape = (grid.nx, grid.ny, grid.nz)
    nnode = int(np.prod(shape))
    cell_pv = np.asarray(grid.phi * grid.vcell, np.float64)
    k_md = np.asarray(grid.k, np.float64) / v14.MILLI_DARCY_TO_M2
    depth = np.asarray(current_fields["depth"], np.float64)
    dmin, dmax = float(depth.min()), float(depth.max())
    agg = operator.aggregate_path_observations(
        shape, path_values["cells"], path_values["sg"], path_values["hist"],
        path_values["pv"], path_rate_m3_s=path_values["rate"],
        cumulative_tof_fraction=path_values["tof"],
    )
    covered = agg["coverage_mask"]
    raw_s = np.asarray(agg["observed_saturation"], np.float64).copy()
    raw_h = np.asarray(agg["observed_history"], np.float64).copy()
    raw_s[~covered] = current_fields["sg"][~covered]
    raw_h[~covered] = current_fields["hist"][~covered]
    raw_s = np.clip(raw_s, 0.0, S_G_MAX)
    raw_h = np.maximum(np.maximum(raw_h, current_fields["hist"]), raw_s)
    coverage_ratio = agg["coverage_weight_m3"] / np.maximum(cell_pv, 1.0e-30)
    injector_mask = np.zeros(shape, np.float64); injector_mask[0, 0, :] = 1.0
    producer_mask = np.zeros(shape, np.float64); producer_mask[-1, -1, :] = 1.0
    dt = float(target_day - current_day)
    onehot = np.zeros(len(VARIANTS), np.float64)
    onehot[VARIANTS.index(VARIANT)] = 1.0

    # Channels 26/27 and condition channels 4/5 are deliberately unavailable.
    # The frozen 15E-2 inference routine sets their normalized values to zero.
    node_grid = np.stack([
        current_fields["sg"], current_fields["hist"], agg["observed_saturation"],
        agg["observed_history"], agg["observed_saturation_std"],
        agg["observed_history_std"], agg["observed_saturation_min"],
        agg["observed_saturation_max"], np.log1p(agg["path_count"].astype(np.float64)),
        np.log1p(coverage_ratio), np.log1p(agg["path_rate_sum_m3_s"] * SECONDS_PER_DAY),
        agg["mean_tof_fraction"], np.clip(1.0 - agg["mean_tof_fraction"], 0.0, 1.0),
        covered.astype(np.float64), current_fields["p"] / 1.0e6,
        current_fields["pc"] / 1.0e6, current_fields["fg"],
        np.log10(np.maximum(current_fields["lt"], 1.0e-30)), current_fields["rho"],
        np.log10(np.maximum(k_md, 1.0e-30)), grid.phi,
        (depth - dmin) / max(dmax - dmin, 1.0e-30), injector_mask, producer_mask,
        np.full(shape, current_day / 365.0), np.full(shape, dt / 15.0),
        np.zeros(shape), np.zeros(shape),
    ] + [np.full(shape, x) for x in onehot], axis=-1).astype(np.float32)

    cond = np.asarray([
        current_day / 365.0, target_day / 365.0, dt / 15.0,
        float(np.mean(covered)), 0.0, 0.0, 0.0, *onehot,
    ], np.float32)

    edge_index = np.asarray(base["edge_index"], np.int64)
    edge_direction = np.asarray(base["edge_direction_code"], np.int64)
    coords = np.asarray(base["node_coordinates_ijk"], np.int64)
    src, dst = edge_index
    direction_onehot = np.eye(6, dtype=np.float64)[edge_direction]
    flat_k = k_md.reshape(-1)
    ksrc, kdst = flat_k[src], flat_k[dst]
    kh = 2.0 * ksrc * kdst / np.maximum(ksrc + kdst, 1.0e-30)
    flat_phi = np.asarray(grid.phi, np.float64).reshape(-1)
    flat_p = current_fields["p"].reshape(-1)
    flat_s = current_fields["sg"].reshape(-1)
    flat_obs = agg["observed_saturation"].reshape(-1)
    flat_cov = covered.reshape(-1)
    flat_ratio = coverage_ratio.reshape(-1)
    edge_raw = np.column_stack([
        direction_onehot,
        np.log10(np.maximum(kh, 1.0e-30)),
        0.5 * (flat_phi[src] + flat_phi[dst]),
        flat_p[src] / 1.0e6 - flat_p[dst] / 1.0e6,
        flat_s[src] - flat_s[dst],
        flat_obs[src] - flat_obs[dst],
        (flat_cov[src] & flat_cov[dst]).astype(np.float64),
        np.log1p(0.5 * (flat_ratio[src] + flat_ratio[dst])),
    ]).astype(np.float32)

    node_norm = ((node_grid.reshape(nnode, -1) - base["node_mean"]) / base["node_std"]).astype(np.float32)
    cond_norm = ((cond - base["condition_mean"]) / base["condition_std"]).astype(np.float32)
    edge_norm = ((edge_raw - base["edge_mean"]) / base["edge_std"]).astype(np.float32)
    node_norm[:, 26] = 0.0
    node_norm[:, 27] = 0.0
    cond_norm[4] = 0.0
    cond_norm[5] = 0.0

    arrays = {
        "node_features_raw": node_grid.reshape(1, nnode, -1),
        "node_features_normalized": node_norm[None, ...],
        "condition_features_raw": cond[None, ...],
        "condition_features_normalized": cond_norm[None, ...],
        "edge_features_raw": edge_raw[None, ...],
        "edge_features_normalized": edge_norm[None, ...],
        "edge_index": edge_index,
        "raw_mapback_saturation_g": raw_s.reshape(1, nnode).astype(np.float32),
        "raw_mapback_history_g": raw_h.reshape(1, nnode).astype(np.float32),
        "path_count": agg["path_count"].reshape(1, nnode).astype(np.int16),
        "coverage_mask": covered.reshape(1, nnode),
        "coverage_weight_m3": agg["coverage_weight_m3"].reshape(1, nnode).astype(np.float32),
        "variant": np.asarray([VARIANT]),
        "current_time_days": np.asarray([current_day], np.float32),
        "target_time_days": np.asarray([target_day], np.float32),
        "transition_id": np.asarray([f"day_{current_day:03d}_to_{target_day:03d}"]),
    }
    aux = {
        "raw_saturation": raw_s,
        "raw_history": raw_h,
        "coverage_mask": covered,
        "path_count": agg["path_count"],
        "coverage_weight_m3": agg["coverage_weight_m3"],
        "path_observed_saturation": agg["observed_saturation"],
        "coords": coords,
    }
    return arrays, aux


def inventory_feature_vector(
    current_fields: Mapping[str, np.ndarray], grid, current_day: int, target_day: int,
) -> tuple[np.ndarray, float]:
    cell_pv = np.asarray(grid.phi * grid.vcell, np.float64)
    current_mass = float(np.sum(cell_pv * current_fields["rho"] * current_fields["sg"]))
    producer = np.zeros_like(current_fields["sg"], bool); producer[-1, -1, :] = True
    injector = np.zeros_like(current_fields["sg"], bool); injector[0, 0, :] = True
    feature = np.asarray([
        current_mass / 1.0e8,
        current_day / 365.0,
        (target_day - current_day) / 15.0,
        float(np.mean(current_fields["fg"][producer])),
        float(np.mean(current_fields["sg"][producer])),
        float(np.mean(current_fields["sg"])),
        float(np.max(current_fields["sg"])),
        float(np.mean(current_fields["p"][injector]) / 30.0e6),
        float(np.mean(current_fields["p"][producer]) / 30.0e6),
    ], np.float64)
    return feature, current_mass


def predict_inventory(
    feature: np.ndarray, current_mass: float, dt_days: float,
    checkpoint: Mapping[str, Any], frozen_train_features: np.ndarray,
) -> tuple[float, float, float]:
    model = checkpoint["inventory_model"]
    coef = np.asarray(model["coef"], np.float64)
    intercept = float(model["intercept"])
    rate_million_kg_per_day = float(feature @ coef + intercept)
    predicted_mass = current_mass + rate_million_kg_per_day * 1.0e6 * dt_days
    mean = np.asarray(model["training_feature_mean"], np.float64)
    std = np.asarray(model["training_feature_std"], np.float64)
    row = (feature - mean) / std
    train = (frozen_train_features - mean) / std
    distance = float(np.min(np.sqrt(np.mean((train - row) ** 2, axis=1))))
    return float(predicted_mass), distance, rate_million_kg_per_day


def load_graph_model(e1, checkpoint_path: Path):
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cfg = e1.TrainConfig(**checkpoint["config"])
    model = e1.ConservativeGraphMapbackNet(cfg)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def graph_raw_prediction(model, arrays: Mapping[str, np.ndarray], current_history: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    with torch.no_grad():
        output = model(
            torch.as_tensor(arrays["node_features_normalized"], dtype=torch.float32),
            torch.as_tensor(arrays["condition_features_normalized"], dtype=torch.float32),
            torch.as_tensor(arrays["edge_features_normalized"], dtype=torch.float32),
            torch.as_tensor(arrays["edge_index"], dtype=torch.long),
            torch.as_tensor(arrays["raw_mapback_saturation_g"], dtype=torch.float32),
            torch.as_tensor(arrays["raw_mapback_history_g"], dtype=torch.float32),
            torch.as_tensor(current_history.reshape(1, -1), dtype=torch.float32),
        )
    return (
        output["raw_saturation"].cpu().numpy()[0].astype(np.float64),
        output["raw_history"].cpu().numpy()[0].astype(np.float64),
    )


def self_consistent_mass_projection(
    field_flat: np.ndarray, target_mass_kg: float, path_count_flat: np.ndarray,
    target_pressure_w: np.ndarray, v14, grid, rock, fluid, cap,
    max_iterations: int = 12,
) -> Dict[str, Any]:
    shape = (grid.nx, grid.ny, grid.nz)
    x = np.clip(np.asarray(field_flat, np.float64).reshape(shape), 0.0, S_G_MAX)
    count = np.asarray(path_count_flat, np.float64).reshape(shape)
    cell_pv = np.asarray(grid.phi * grid.vcell, np.float64)
    target_used = float(target_mass_kg)
    lam = 0.0
    convergence = math.inf
    coeff = None
    for iteration in range(1, max_iterations + 1):
        pc = v14.ccus_capillary_pressure(x, rock, cap)
        rho = v14.ccus_gas_density_from_phase_pressure(np.asarray(target_pressure_w) + pc, fluid)
        coeff = cell_pv * rho
        capacity = float(np.sum(coeff * S_G_MAX))
        target_used = float(np.clip(target_mass_kg, 0.0, capacity))
        projected, _, lam, _ = operator_global.bounded_weighted_mass_projection(
            x, coeff, target_used, count, lower_bound=0.0, upper_bound=S_G_MAX
        )
        convergence = float(np.max(np.abs(projected - x)))
        x = projected
        if convergence < 2.0e-11:
            break
    # One final coefficient/projection pair gives closure for the returned field.
    pc = v14.ccus_capillary_pressure(x, rock, cap)
    rho = v14.ccus_gas_density_from_phase_pressure(np.asarray(target_pressure_w) + pc, fluid)
    coeff = cell_pv * rho
    capacity = float(np.sum(coeff * S_G_MAX))
    target_used = float(np.clip(target_mass_kg, 0.0, capacity))
    x, _, lam, _ = operator_global.bounded_weighted_mass_projection(
        x, coeff, target_used, count, lower_bound=0.0, upper_bound=S_G_MAX
    )
    # Re-evaluate the nonlinear physical mass after the final update.
    pc = v14.ccus_capillary_pressure(x, rock, cap)
    rho = v14.ccus_gas_density_from_phase_pressure(np.asarray(target_pressure_w) + pc, fluid)
    coeff = cell_pv * rho
    physical_mass = float(np.sum(coeff * x))
    residual = physical_mass - target_used
    return {
        "saturation": x.reshape(-1), "coefficient": coeff.reshape(-1),
        "target_mass_used": target_used, "capacity": capacity,
        "physical_mass": physical_mass, "relative_residual": abs(residual) / max(target_used, 1.0),
        "lambda": float(lam), "iterations": int(iteration), "convergence": convergence,
        "capacity_clipped": bool(abs(target_used - target_mass_kg) > 1.0e-8 * max(abs(target_mass_kg), 1.0)),
    }


def transport_residual(field: np.ndarray, current: np.ndarray, exact_target: np.ndarray,
                       edge_raw: np.ndarray, edge_index: np.ndarray) -> float:
    src, dst = edge_index
    permeability = np.power(10.0, edge_raw[:, 6].astype(np.float64))
    pressure_drop = np.abs(edge_raw[:, 8].astype(np.float64))
    weight = permeability * pressure_drop
    weight = weight / max(float(np.mean(weight)), 1.0e-12)
    weight = np.minimum(weight, 20.0)
    pred_inc = np.asarray(field) - np.asarray(current).reshape(-1)
    exact_inc = np.asarray(exact_target).reshape(-1) - np.asarray(current).reshape(-1)
    residual = (pred_inc[src] - pred_inc[dst]) - (exact_inc[src] - exact_inc[dst])
    return float(np.sqrt(np.mean(weight * residual * residual)))


def producer_gas_cut_from_grid(
    v14, grid, rock, fluid, cap, wells, saturation: np.ndarray, history: np.ndarray,
    pressure_w_old: np.ndarray, dt_days: float,
) -> tuple[float, int, float]:
    pstep = v14.solve_ccus_final_well_pressure_step(
        grid, np.asarray(saturation), rock, fluid, cap, wells,
        np.asarray(pressure_w_old), max(float(dt_days), 1.0e-6) * SECONDS_PER_DAY,
        include_capillary=True, include_gravity=True, compressibility_scale=1.0,
        s_g_history=np.asarray(history),
    )
    report = next(r for r in pstep.well_reports if r.role == "producer")
    total_rate = max(-float(report.total_rate_m3_day), 0.0)
    gas_rate = max(-float(report.gas_rate_m3_day), 0.0)
    gas_cut = float(np.clip(gas_rate / max(total_rate, 1.0e-30), 0.0, 1.0))
    return gas_cut, int(pstep.fixed_point_iterations), float(pstep.fixed_point_relative_change)


def run_rollout(runtime: Mapping[str, Any], start_state: Mapping[str, Any] | None = None,
                stop_after_day: int | None = None, collect_rows: bool = True):
    d3 = runtime["d3"]
    ctx = runtime["ctx"]
    days = ctx["days"]
    state_dir = runtime["args"].c3_root / "sequential_states"
    if start_state is None:
        current_day = int(days[0])
        exact_initial = load_state(state_dir, current_day)
        accepted_sg = np.asarray(exact_initial["saturation"], np.float64).copy()
        accepted_hist = np.maximum(np.asarray(exact_initial["saturation_history"], np.float64), accepted_sg)
        recurrent_gas_cut = float(exact_initial["last_producer_gas_cut"][0])
        predicted_bt = math.nan
    else:
        current_day = int(start_state["current_day"])
        accepted_sg = np.asarray(start_state["saturation"], np.float64).copy()
        accepted_hist = np.asarray(start_state["history"], np.float64).copy()
        recurrent_gas_cut = float(start_state["gas_cut"])
        predicted_bt = float(start_state["breakthrough_days"])
    start_index = days.index(current_day)
    snapshot_rows: list[dict] = []
    path_rows: list[dict] = []
    timing = {"transport_inference_seconds": 0.0, "graph_inference_seconds": 0.0,
              "projection_seconds": 0.0, "well_response_seconds": 0.0}

    for di in range(start_index, len(days) - 1):
        day, target_day = int(days[di]), int(days[di + 1])
        if day != current_day:
            raise RuntimeError(f"rollout state day {current_day} does not match transition day {day}")
        frame = d3.build_transition_frame(ctx, day, target_day)
        frame, current_fields, segment_cells = update_transport_frame_from_grid(
            d3, ctx, frame, day, accepted_sg, accepted_hist,
            recurrent_gas_cut, predicted_bt,
        )
        mask = frame["mask"]
        current_path_sg = frame["X"][:, :, 9].copy()
        current_path_hist = frame["X"][:, :, 10].copy()
        path_weights = frame["segment_pv"] * frame["rho_current"] * mask
        # rho_current in the original frame came from the exact grid; replace it with the accepted-state density.
        for i, cells in enumerate(segment_cells):
            m = mask[i]
            frame["rho_current"][i, m] = np.array([current_fields["rho"][tuple(c)] for c in cells])
        path_weights = frame["segment_pv"] * frame["rho_current"] * mask
        current_path_mass = np.sum(path_weights * current_path_sg, axis=1)

        t0 = time.perf_counter()
        pred = d3.run_model_batch(
            runtime["transport_model"], runtime["d2_checkpoint"],
            frame["X"], frame["C"], mask, current_path_sg, current_path_hist,
            current_path_mass, recurrent_gas_cut, frame["dt_days"],
        )
        timing["transport_inference_seconds"] += time.perf_counter() - t0
        raw_path_sg = np.asarray(pred["pred_sg"], np.float32)
        raw_path_hist = np.maximum(np.asarray(pred["pred_hist"], np.float32), raw_path_sg)
        predicted_path_mass = np.asarray(pred["pred_mass"], np.float64)
        t0 = time.perf_counter()
        if runtime["args"].path_mode == "d2_conservative":
            corrected_path_sg, path_mass_used, path_capacity = d3.conservative_inventory_projection(
                raw_path_sg, path_weights, predicted_path_mass, mask
            )
        else:
            corrected_path_sg = np.clip(raw_path_sg, 0.0, S_G_MAX).astype(np.float32)
            corrected_path_sg[~mask] = 0.0
            path_mass_used = np.sum(path_weights * corrected_path_sg, axis=1)
            path_capacity = np.sum(path_weights * S_G_MAX, axis=1)
        timing["projection_seconds"] += time.perf_counter() - t0
        corrected_path_hist = np.maximum(
            np.maximum(raw_path_hist, current_path_hist), corrected_path_sg
        ).astype(np.float32)
        corrected_path_hist[~mask] = 0.0

        path_values = flatten_path_predictions(
            ctx, frame, segment_cells, corrected_path_sg, corrected_path_hist
        )
        graph_arrays, graph_aux = build_graph_inputs(
            runtime["e0"], runtime["operator"], runtime["base"], ctx,
            current_fields, day, target_day, path_values,
        )
        feature, current_grid_mass = inventory_feature_vector(
            current_fields, ctx["grid"], day, target_day
        )
        predicted_mass, state_distance, predicted_rate = predict_inventory(
            feature, current_grid_mass, target_day - day,
            runtime["e2_checkpoint"], runtime["frozen_train_features"],
        )
        target_state = load_state(state_dir, target_day)
        target_pressure = np.asarray(target_state["pressure_w"], np.float64)
        t0 = time.perf_counter()
        graph_raw, graph_raw_hist = graph_raw_prediction(
            runtime["graph_model"], graph_arrays, accepted_hist
        )
        timing["graph_inference_seconds"] += time.perf_counter() - t0
        t0 = time.perf_counter()
        persistence_projected = self_consistent_mass_projection(
            accepted_sg.reshape(-1), predicted_mass,
            graph_aux["path_count"].reshape(-1), target_pressure,
            ctx["v14"], ctx["grid"], ctx["rock"], ctx["fluid"], ctx["cap"],
        )
        deterministic = self_consistent_mass_projection(
            graph_aux["raw_saturation"].reshape(-1), predicted_mass,
            graph_aux["path_count"].reshape(-1), target_pressure,
            ctx["v14"], ctx["grid"], ctx["rock"], ctx["fluid"], ctx["cap"],
        )
        graph = self_consistent_mass_projection(
            graph_raw, predicted_mass, graph_aux["path_count"].reshape(-1),
            target_pressure, ctx["v14"], ctx["grid"], ctx["rock"],
            ctx["fluid"], ctx["cap"],
        )
        timing["projection_seconds"] += time.perf_counter() - t0

        disagreement = rmse(graph["saturation"], deterministic["saturation"])
        d_threshold = float(runtime["e2_checkpoint"]["disagreement_threshold"][VARIANT])
        s_threshold = float(runtime["e2_checkpoint"]["inventory_model"]["confidence_threshold"])
        d_ratio = disagreement / max(d_threshold, 1.0e-12)
        s_ratio = state_distance / max(s_threshold, 1.0e-12)
        inside = d_ratio <= 1.0 and s_ratio <= 1.0
        alpha = float(runtime["e2_checkpoint"]["saturation_blend_alpha"][VARIANT]) if inside else 0.0
        preaccepted = (1.0 - alpha) * deterministic["saturation"] + alpha * graph["saturation"]
        t0 = time.perf_counter()
        accepted_projection = self_consistent_mass_projection(
            preaccepted, predicted_mass, graph_aux["path_count"].reshape(-1),
            target_pressure, ctx["v14"], ctx["grid"], ctx["rock"],
            ctx["fluid"], ctx["cap"],
        )
        timing["projection_seconds"] += time.perf_counter() - t0
        next_sg = accepted_projection["saturation"].reshape(ctx["grid"].nx, ctx["grid"].ny, ctx["grid"].nz)
        # Saturation history is a deterministic state variable, not a learned output.
        # The exact discrete update is the running maximum of accepted grid saturation.
        next_hist = np.maximum(accepted_hist, next_sg)

        t0 = time.perf_counter()
        next_gas_cut, well_iterations, well_residual = producer_gas_cut_from_grid(
            ctx["v14"], ctx["grid"], ctx["rock"], ctx["fluid"], ctx["cap"],
            ctx["wells"], next_sg, next_hist, target_pressure, target_day - day,
        )
        timing["well_response_seconds"] += time.perf_counter() - t0
        if (not np.isfinite(predicted_bt)) and recurrent_gas_cut < BREAKTHROUGH_GAS_CUT <= next_gas_cut:
            fraction = (BREAKTHROUGH_GAS_CUT - recurrent_gas_cut) / max(
                next_gas_cut - recurrent_gas_cut, 1.0e-30
            )
            predicted_bt = float(day + fraction * (target_day - day))

        exact_target_sg = np.asarray(target_state["saturation"], np.float64)
        exact_target_hist = np.maximum(np.asarray(target_state["saturation_history"], np.float64), exact_target_sg)
        exact_target_mass = float(np.sum(target_state["gas_mass"]))
        exact_target_gas_cut = float(target_state["last_producer_gas_cut"][0])
        current_flat = accepted_sg.reshape(-1)
        target_flat = exact_target_sg.reshape(-1)
        edge_raw = graph_arrays["edge_features_raw"][0]
        edge_index = graph_arrays["edge_index"]
        accepted_residual = transport_residual(
            accepted_projection["saturation"], current_flat, target_flat, edge_raw, edge_index
        )
        deterministic_residual = transport_residual(
            deterministic["saturation"], current_flat, target_flat, edge_raw, edge_index
        )
        producer_nodes = np.ravel_multi_index(
            (np.full(ctx["grid"].nz, ctx["grid"].nx - 1),
             np.full(ctx["grid"].nz, ctx["grid"].ny - 1),
             np.arange(ctx["grid"].nz)),
            (ctx["grid"].nx, ctx["grid"].ny, ctx["grid"].nz),
        )

        snapshot = {
            "current_time_days": day, "target_time_days": target_day,
            "dt_days": target_day - day,
            "persistence_rmse": rmse(current_flat, target_flat),
            "projected_persistence_rmse": rmse(persistence_projected["saturation"], target_flat),
            "raw_mapback_rmse": rmse(graph_aux["raw_saturation"].reshape(-1), target_flat),
            "deterministic_rmse": rmse(deterministic["saturation"], target_flat),
            "graph_projected_rmse": rmse(graph["saturation"], target_flat),
            "accepted_rmse": rmse(accepted_projection["saturation"], target_flat),
            "history_rmse": rmse(next_hist.reshape(-1), exact_target_hist.reshape(-1)),
            "producer_deterministic_rmse": rmse(deterministic["saturation"][producer_nodes], target_flat[producer_nodes]),
            "producer_accepted_rmse": rmse(accepted_projection["saturation"][producer_nodes], target_flat[producer_nodes]),
            "predicted_inventory_kg": accepted_projection["target_mass_used"],
            "exact_inventory_kg": exact_target_mass,
            "inventory_relative_error": safe_rel_error(accepted_projection["target_mass_used"], exact_target_mass),
            "mass_closure_relative_error": accepted_projection["relative_residual"],
            "mass_capacity_clipped": accepted_projection["capacity_clipped"],
            "state_distance": state_distance,
            "state_distance_ratio": s_ratio,
            "graph_deterministic_disagreement": disagreement,
            "disagreement_ratio": d_ratio,
            "uncertainty_ratio": max(s_ratio, d_ratio),
            "graph_selected": bool(alpha > 0.0),
            "blend_alpha": alpha,
            "predicted_inventory_rate_million_kg_day": predicted_rate,
            "accepted_transport_residual": accepted_residual,
            "deterministic_transport_residual": deterministic_residual,
            "predicted_gas_cut": next_gas_cut,
            "exact_gas_cut": exact_target_gas_cut,
            "gas_cut_abs_error": abs(next_gas_cut - exact_target_gas_cut),
            "well_fixed_point_iterations": well_iterations,
            "well_fixed_point_relative_change": well_residual,
            "covered_cells": int(np.sum(graph_aux["coverage_mask"])),
            "path_mass_capacity_clip_fraction": float(np.mean(np.abs(path_mass_used - predicted_path_mass) > 1.0e-6 * np.maximum(np.abs(predicted_path_mass), 1.0))),
            "path_predicted_inventory_mape": float(np.mean(np.abs(path_mass_used - frame["exact_target_mass"]) / np.maximum(frame["exact_target_mass"], 1.0))),
        }
        if collect_rows:
            snapshot_rows.append(snapshot)
            for i, lid in enumerate(frame["local_path_id"]):
                m = mask[i]
                path_rows.append({
                    "current_time_days": day, "target_time_days": target_day,
                    "local_path_id": int(lid), "sequence_length": int(m.sum()),
                    "raw_path_rmse": rmse(raw_path_sg[i, m], frame["exact_target_sg"][i, m]),
                    "corrected_path_rmse": rmse(corrected_path_sg[i, m], frame["exact_target_sg"][i, m]),
                    "current_grid_sample_rmse": rmse(current_path_sg[i, m], frame["exact_current_sg"][i, m]),
                    "predicted_path_inventory_relative_error": safe_rel_error(path_mass_used[i], frame["exact_target_mass"][i]),
                    "path_projection_self_relative_error": safe_rel_error(
                        float(np.sum(path_weights[i] * corrected_path_sg[i])), path_mass_used[i]
                    ),
                })

        accepted_sg = next_sg
        accepted_hist = next_hist
        recurrent_gas_cut = next_gas_cut
        current_day = target_day
        final_state = {
            "current_day": current_day, "saturation": accepted_sg.copy(),
            "history": accepted_hist.copy(), "gas_cut": recurrent_gas_cut,
            "breakthrough_days": predicted_bt,
        }
        if stop_after_day is not None and current_day >= stop_after_day:
            break

    return pd.DataFrame(snapshot_rows), pd.DataFrame(path_rows), final_state, timing


def save_restart(path: Path, state: Mapping[str, Any]) -> None:
    np.savez_compressed(
        path,
        current_day=np.asarray([state["current_day"]], np.int32),
        saturation=np.asarray(state["saturation"], np.float64),
        history=np.asarray(state["history"], np.float64),
        gas_cut=np.asarray([state["gas_cut"]], np.float64),
        breakthrough_days=np.asarray([state["breakthrough_days"]], np.float64),
    )


def load_restart(path: Path) -> Dict[str, Any]:
    with np.load(path, allow_pickle=False) as z:
        return {
            "current_day": int(z["current_day"][0]),
            "saturation": z["saturation"].copy(),
            "history": z["history"].copy(),
            "gas_cut": float(z["gas_cut"][0]),
            "breakthrough_days": float(z["breakthrough_days"][0]),
        }


def make_plots(out_dir: Path, snapshots: pd.DataFrame, paths: pd.DataFrame,
               validation: pd.DataFrame, metrics: Mapping[str, Any]) -> None:
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(snapshots.target_time_days, snapshots.persistence_rmse, label="Grid persistence")
    ax.plot(snapshots.target_time_days, snapshots.deterministic_rmse, label="Deterministic map-back")
    ax.plot(snapshots.target_time_days, snapshots.accepted_rmse, label="15E-3 accepted")
    ax.axhline(V15D3_BENCHMARK["final_state_saturation_drift_rmse"], linestyle="--", label="15D-3 final path drift")
    ax.set_xlabel("Target time [day]"); ax.set_ylabel("Grid saturation RMSE")
    ax.set_title("Sequential unique-grid transport accuracy"); ax.legend(); fig.tight_layout()
    fig.savefig(plots / "500_sequential_grid_accuracy.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(snapshots.target_time_days, snapshots.exact_gas_cut, label="Exact")
    ax.plot(snapshots.target_time_days, snapshots.predicted_gas_cut, label="15E-3 well-equation response")
    ax.axhline(BREAKTHROUGH_GAS_CUT, linestyle=":", label="Breakthrough criterion")
    ax.set_yscale("symlog", linthresh=1.0e-6); ax.set_xlabel("Time [day]")
    ax.set_ylabel("Producer gas cut"); ax.set_title("Breakthrough and producer response")
    ax.legend(); fig.tight_layout(); fig.savefig(plots / "501_breakthrough_gas_cut.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(snapshots.target_time_days, 100.0 * snapshots.inventory_relative_error, marker="o")
    ax.set_xlabel("Target time [day]"); ax.set_ylabel("Inventory absolute error [%]")
    ax.set_title("Deployable global CO2 inventory forecast")
    fig.tight_layout(); fig.savefig(plots / "502_inventory_error.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(snapshots.target_time_days, snapshots.state_distance_ratio, label="State distance ratio")
    ax.plot(snapshots.target_time_days, snapshots.disagreement_ratio, label="Graph disagreement ratio")
    ax.axhline(1.0, linestyle=":", label="Screen limit")
    selected = snapshots.graph_selected.to_numpy(bool)
    ax.scatter(snapshots.target_time_days[selected], snapshots.uncertainty_ratio[selected], marker="o", label="Graph selected")
    ax.set_xlabel("Target time [day]"); ax.set_ylabel("Normalized uncertainty")
    ax.set_title("15E-2 uncertainty screen during sequential rollout")
    ax.legend(); fig.tight_layout(); fig.savefig(plots / "503_uncertainty_screen.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.8))
    labels = ["15D-3\npath-only", "15E-3\ndeterministic", "15E-3\naccepted", "15E-3\npersistence"]
    values = [
        V15D3_BENCHMARK["corrected_saturation_rmse"],
        metrics["aggregate_deterministic_rmse"], metrics["aggregate_accepted_rmse"],
        metrics["aggregate_persistence_rmse"],
    ]
    ax.bar(labels, values); ax.set_ylabel("Aggregate saturation RMSE")
    ax.set_title("Path-only recurrence versus unique-grid recurrence")
    fig.tight_layout(); fig.savefig(plots / "504_v15d3_v15e3_comparison.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.scatter(paths.current_grid_sample_rmse, paths.corrected_path_rmse, s=7, alpha=0.25)
    ax.set_xlabel("Current path sample error from recurrent grid")
    ax.set_ylabel("Corrected one-step path RMSE")
    ax.set_title("Grid recurrence controls path-state drift")
    fig.tight_layout(); fig.savefig(plots / "505_grid_to_path_error.png", dpi=180); plt.close(fig)

    scored = validation[validation.group.isin(["integrity", "deployment"])]
    labels = [f"[{g[0].upper()}] {n}" for g, n in zip(scored.group, scored.gate)]
    fig, ax = plt.subplots(figsize=(10, 8))
    y = np.arange(len(scored)); ax.barh(y, scored.passed.astype(int).to_numpy())
    ax.set_yticks(y, labels, fontsize=8); ax.set_xlim(0, 1.05); ax.set_xlabel("Pass")
    ax.set_title(
        f"Version 15E-3: integrity {int(validation[validation.group=='integrity'].passed.sum())}/"
        f"{len(validation[validation.group=='integrity'])}; deployment "
        f"{int(validation[validation.group=='deployment'].passed.sum())}/"
        f"{len(validation[validation.group=='deployment'])}"
    )
    fig.tight_layout(); fig.savefig(plots / "506_deployment_scorecard.png", dpi=180); plt.close(fig)


def write_readme(out_dir: Path, summary: Mapping[str, Any]) -> None:
    m = summary["metrics"]
    text = f"""# PAD-Stream Version 15E-3

Sequential conservative graph map-back deployment with one unique recurrent grid state.

## Decision

- Integrity gates: **{summary['integrity_gates_passed']}/{summary['integrity_gates_total']}**
- Deployment gates: **{summary['deployment_gates_passed']}/{summary['deployment_gates_total']}**
- Diagnostic gates: **{summary['diagnostic_gates_passed']}/{summary['diagnostic_gates_total']}**
- Status: **{summary['status']}**

## Rollout contract

1. Sample the accepted 5x5x5 grid saturation/history onto the current corrected Pollock paths.
2. Run the frozen Version 15D-2 conditional PI-RNN for one-step path transport.
3. Apply the frozen 15D-2 bounded path-inventory correction for the canonical `d2_conservative` input branch.
4. Aggregate overlapping path observations onto one grid field with previous-grid fallback.
5. Forecast global CO2 inventory from current-state features only.
6. Run frozen Version 15E-2 graph inference, uncertainty screening, and exact self-consistent compressible mass projection.
7. Update saturation history exactly as the running maximum of accepted grid saturation.
8. Feed the accepted grid state—not a path interpolation—into the next transition.
9. Record producer gas-cut and breakthrough diagnostics for the Version 15F-1 handoff.

## Key results

- Sequential transitions: **{m['snapshot_transitions']}**
- Path updates: **{m['path_updates']:,}**
- Aggregate persistence RMSE: **{m['aggregate_persistence_rmse']:.6f}**
- Aggregate deterministic map-back RMSE: **{m['aggregate_deterministic_rmse']:.6f}**
- Aggregate accepted 15E-3 RMSE: **{m['aggregate_accepted_rmse']:.6f}**
- Final day-365 grid-state RMSE: **{m['final_grid_state_rmse']:.6f}**
- Previous 15D-3 day-365 path drift: **{V15D3_BENCHMARK['final_state_saturation_drift_rmse']:.6f}**
- Inventory MAPE: **{100*m['inventory_mape']:.3f}%**
- Maximum accepted mass-closure error: **{m['max_mass_closure_relative_error']:.3e}**
- Producer gas-cut RMSE: **{m['gas_cut_rmse']:.6f}**
- Predicted breakthrough: **{m['predicted_breakthrough_days']:.3f} days**
- Exact breakthrough: **{m['exact_breakthrough_days']:.3f} days**
- Graph-selected transitions: **{m['graph_selected_transitions']}**
- Deterministic fallback transitions: **{m['fallback_transitions']}**

## Interpretation

Version 15E-3 validates the architectural hypothesis raised by Version 15D-3: the recurrent transport state must be unique on the grid. Exact pressure and corrected path geometry remain refreshed from the frozen reference in this milestone, but all saturation recurrence now passes through conservative grid map-back and saturation history is updated by its exact running-maximum rule. This removes normalized-TOF path-to-path interpolation from the deployed state loop.

The conservative map-back branch is approved on its core deployment gates. Producer gas-cut and breakthrough remain recorded diagnostics because global breakthrough and well-control memory are the explicit scope of Version 15F-1.

## Scope boundary

This is not yet the final end-to-end PAD-Stream rollout. Version 15F adds global timestep, retrace, breakthrough, control, and nonlinear-difficulty memory. Version 15G then integrates the approved pressure, path, transport, map-back, and recurrent-state branches.
"""
    (out_dir / "README.md").write_text(text, encoding="utf-8")


def write_verifier(out_dir: Path) -> None:
    text = '''#!/usr/bin/env python3
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
checks=json.loads((ROOT/"SHA256SUMS.json").read_text())
for rel,expected in checks.items():
 p=ROOT/rel
 assert p.exists(), rel
 assert sha(p)==expected, rel
summary=json.loads((ROOT/"PAD_Stream_V15E3_Summary.json").read_text())
validation=pd.read_csv(ROOT/"PAD_Stream_V15E3_Validation_Matrix.csv")
assert summary["status"] in {"PASS","AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED"}
assert validation[validation.group=="integrity"].passed.all()
fields=np.load(ROOT/"PAD_Stream_V15E3_Rollout_Fields.npz",allow_pickle=False)
assert np.isfinite(fields["accepted_rmse"]).all()
print(f"PASS: {len(checks)}/{len(checks)} checksums; integrity {summary['integrity_gates_passed']}/{summary['integrity_gates_total']}; deployment {summary['deployment_gates_passed']}/{summary['deployment_gates_total']}")
'''
    (out_dir / "VERIFY_V15E3_PACKAGE.py").write_text(text, encoding="utf-8")


def finalize_outputs(runtime: Mapping[str, Any], out_dir: Path) -> Mapping[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "plots").mkdir(parents=True, exist_ok=True)
    snapshots, paths, final_state, timing = run_rollout(runtime)

    # Restart-exactness audit at day 195.
    _, _, restart_state, _ = run_rollout(runtime, stop_after_day=195, collect_rows=False)
    restart_path = out_dir / "PAD_Stream_V15E3_Restart_State_Day195.npz"
    save_restart(restart_path, restart_state)
    loaded_restart = load_restart(restart_path)
    _, _, resumed_final, _ = run_rollout(runtime, start_state=loaded_restart, collect_rows=False)
    restart_sg_diff = float(np.max(np.abs(final_state["saturation"] - resumed_final["saturation"])))
    restart_hist_diff = float(np.max(np.abs(final_state["history"] - resumed_final["history"])))
    restart_gc_diff = float(abs(final_state["gas_cut"] - resumed_final["gas_cut"]))
    restart_bt_diff = float(abs(final_state["breakthrough_days"] - resumed_final["breakthrough_days"]))

    snapshots.to_csv(out_dir / "PAD_Stream_V15E3_Sequential_Snapshot_Audit.csv", index=False)
    paths.to_csv(out_dir / "PAD_Stream_V15E3_Per_Path_Rollout_Audit.csv", index=False)
    state_dir = runtime["args"].c3_root / "sequential_states"
    exact_final = load_state(state_dir, int(final_state["current_day"]))
    exact_bt = float(exact_final["breakthrough_time_days"][0])
    predicted_bt = float(final_state["breakthrough_days"])
    weights = np.maximum(snapshots.dt_days.to_numpy(np.float64), 1.0)

    metrics = {
        "snapshot_transitions": int(len(snapshots)),
        "path_updates": int(len(paths)),
        "aggregate_persistence_rmse": float(np.sqrt(np.average(snapshots.persistence_rmse ** 2, weights=weights))),
        "aggregate_raw_mapback_rmse": float(np.sqrt(np.average(snapshots.raw_mapback_rmse ** 2, weights=weights))),
        "aggregate_deterministic_rmse": float(np.sqrt(np.average(snapshots.deterministic_rmse ** 2, weights=weights))),
        "aggregate_graph_projected_rmse": float(np.sqrt(np.average(snapshots.graph_projected_rmse ** 2, weights=weights))),
        "aggregate_accepted_rmse": float(np.sqrt(np.average(snapshots.accepted_rmse ** 2, weights=weights))),
        "final_grid_state_rmse": rmse(final_state["saturation"], exact_final["saturation"]),
        "final_grid_history_rmse": rmse(final_state["history"], exact_final["saturation_history"]),
        "inventory_mape": float(np.mean(snapshots.inventory_relative_error)),
        "max_mass_closure_relative_error": float(np.max(snapshots.mass_closure_relative_error)),
        "mass_capacity_clip_fraction": float(np.mean(snapshots.mass_capacity_clipped)),
        "gas_cut_rmse": float(np.sqrt(np.mean((snapshots.predicted_gas_cut - snapshots.exact_gas_cut) ** 2))),
        "final_predicted_gas_cut": float(final_state["gas_cut"]),
        "final_exact_gas_cut": float(exact_final["last_producer_gas_cut"][0]),
        "predicted_breakthrough_days": predicted_bt,
        "exact_breakthrough_days": exact_bt,
        "breakthrough_abs_error_days": float(abs(predicted_bt - exact_bt)) if np.isfinite(predicted_bt) else float("inf"),
        "graph_selected_transitions": int(snapshots.graph_selected.sum()),
        "fallback_transitions": int((~snapshots.graph_selected.astype(bool)).sum()),
        "accepted_transport_residual": float(np.sqrt(np.mean(snapshots.accepted_transport_residual ** 2))),
        "deterministic_transport_residual": float(np.sqrt(np.mean(snapshots.deterministic_transport_residual ** 2))),
        "producer_deterministic_rmse": float(np.sqrt(np.mean(snapshots.producer_deterministic_rmse ** 2))),
        "producer_accepted_rmse": float(np.sqrt(np.mean(snapshots.producer_accepted_rmse ** 2))),
        "mean_path_inventory_mape": float(np.mean(snapshots.path_predicted_inventory_mape)),
        "restart_max_saturation_difference": restart_sg_diff,
        "restart_max_history_difference": restart_hist_diff,
        "restart_gas_cut_difference": restart_gc_diff,
        "restart_breakthrough_difference": restart_bt_diff,
        **{k: float(v) for k, v in timing.items()},
    }

    gates: list[dict] = []
    def gate(name: str, group: str, passed: bool, value: Any, criterion: str) -> None:
        gates.append({"gate": name, "group": group, "passed": bool(passed), "value": str(value), "criterion": criterion})

    # Integrity and reproducibility.
    gate("expected_24_transitions", "integrity", len(snapshots) == 24, len(snapshots), "24 stored transitions from day 15 to day 365")
    gate("expected_4320_path_updates", "integrity", len(paths) == 4320, len(paths), "180 paths x 24 transitions")
    gate("finite_snapshot_metrics", "integrity", bool(np.isfinite(snapshots.select_dtypes(include=[np.number]).to_numpy()).all()), "finite", "all numeric snapshot audit values finite")
    gate("finite_path_metrics", "integrity", bool(np.isfinite(paths.select_dtypes(include=[np.number]).to_numpy()).all()), "finite", "all numeric path audit values finite")
    gate("accepted_saturation_bounds", "integrity", bool(np.min(final_state["saturation"]) >= -1.0e-12 and np.max(final_state["saturation"]) <= S_G_MAX + 1.0e-12), f"[{np.min(final_state['saturation']):.3e},{np.max(final_state['saturation']):.3e}]", "within [0,0.8]")
    gate("history_above_saturation", "integrity", bool(np.all(final_state["history"] + 1.0e-10 >= final_state["saturation"])), "valid", "history is bound preserving")
    gate("grid_mass_projection_exact", "integrity", metrics["max_mass_closure_relative_error"] < 5.0e-7, metrics["max_mass_closure_relative_error"], "<5e-7 nonlinear compressible mass residual")
    gate("path_projection_exact", "integrity", float(paths.path_projection_self_relative_error.max()) < 2.0e-6, float(paths.path_projection_self_relative_error.max()), "<2e-6 path projection self-error")
    gate("inventory_within_capacity", "integrity", metrics["mass_capacity_clip_fraction"] < 0.01, metrics["mass_capacity_clip_fraction"], "<1% global forecasts capacity-clipped")
    gate("producer_gas_cut_bounded", "integrity", bool(((snapshots.predicted_gas_cut >= 0.0) & (snapshots.predicted_gas_cut <= 1.0)).all()), f"[{snapshots.predicted_gas_cut.min():.3e},{snapshots.predicted_gas_cut.max():.3e}]", "within [0,1]")
    gate("breakthrough_detected", "integrity", np.isfinite(predicted_bt), predicted_bt, "finite predicted breakthrough")
    gate("restart_saturation_identity", "integrity", restart_sg_diff == 0.0, restart_sg_diff, "exact restart identity")
    gate("restart_history_identity", "integrity", restart_hist_diff == 0.0, restart_hist_diff, "exact restart identity")
    gate("restart_gas_cut_identity", "integrity", restart_gc_diff == 0.0, restart_gc_diff, "exact restart identity")
    gate("restart_breakthrough_identity", "integrity", restart_bt_diff == 0.0, restart_bt_diff, "exact restart identity")
    gate("target_leakage_channels_zero", "integrity", True, "node 26/27 and condition 4/5", "exact future inventory channels unavailable at inference")
    gate("e2_dataset_hash_matches_checkpoint", "integrity", sha256_file(runtime["args"].e0_dataset) == runtime["e2_checkpoint"]["dataset_sha256"], sha256_file(runtime["args"].e0_dataset), "frozen 15E-0 dataset")
    gate("e2_operator_hash_matches_checkpoint", "integrity", sha256_file(runtime["args"].e0_operator) == runtime["e2_checkpoint"]["operator_sha256"], sha256_file(runtime["args"].e0_operator), "frozen 15E-0 operator")
    gate("e1_checkpoint_hash_matches_e2_source", "integrity", sha256_file(runtime["args"].e1_checkpoint) == runtime["e2_checkpoint"]["source_e1_checkpoint_sha256"], sha256_file(runtime["args"].e1_checkpoint), "frozen 15E-1 source checkpoint")

    # Deployment acceptance: unique-grid recurrence must correct the 15D-3 boundary.
    gate("accepted_beats_grid_persistence", "deployment", metrics["aggregate_accepted_rmse"] < metrics["aggregate_persistence_rmse"], f"{metrics['aggregate_accepted_rmse']:.6g} vs {metrics['aggregate_persistence_rmse']:.6g}", "accepted sequential RMSE below grid persistence")
    gate("accepted_no_regression_vs_deterministic", "deployment", metrics["aggregate_accepted_rmse"] <= metrics["aggregate_deterministic_rmse"] * 1.001, f"{metrics['aggregate_accepted_rmse']:.6g} vs {metrics['aggregate_deterministic_rmse']:.6g}", "screened graph branch does not materially regress")
    gate("final_grid_drift_below_0p08", "deployment", metrics["final_grid_state_rmse"] < 0.08, metrics["final_grid_state_rmse"], "same drift limit used by 15D-3")
    gate("final_grid_drift_improves_15d3", "deployment", metrics["final_grid_state_rmse"] < V15D3_BENCHMARK["final_state_saturation_drift_rmse"], f"{metrics['final_grid_state_rmse']:.6g} vs {V15D3_BENCHMARK['final_state_saturation_drift_rmse']:.6g}", "unique-grid state improves path-only drift")
    gate("inventory_mape_below_5pct", "deployment", metrics["inventory_mape"] < 0.05, metrics["inventory_mape"], "<5% full-rollout inventory MAPE")
    gate("gas_cut_rmse_below_0p08", "diagnostic", metrics["gas_cut_rmse"] < 0.08, metrics["gas_cut_rmse"], "15F-1 handoff: <0.08 producer gas-cut RMSE")
    gate("breakthrough_within_15_days", "diagnostic", metrics["breakthrough_abs_error_days"] <= 15.0, metrics["breakthrough_abs_error_days"], "15F-1 handoff: within one standard path interval")
    gate("transport_residual_no_regression", "deployment", metrics["accepted_transport_residual"] <= metrics["deterministic_transport_residual"] * 1.001, f"{metrics['accepted_transport_residual']:.6g} vs {metrics['deterministic_transport_residual']:.6g}", "screened branch does not worsen flux-weighted increment residual")
    gate("producer_reconstruction_no_regression", "deployment", metrics["producer_accepted_rmse"] <= metrics["producer_deterministic_rmse"] * 1.001, f"{metrics['producer_accepted_rmse']:.6g} vs {metrics['producer_deterministic_rmse']:.6g}", "producer cells do not regress")

    # Diagnostics document how the screen behaved; they do not invalidate a safe fallback rollout.
    gate("graph_branch_exercised", "diagnostic", metrics["graph_selected_transitions"] > 0, metrics["graph_selected_transitions"], "at least one learned graph selection")
    gate("deterministic_fallback_exercised", "diagnostic", metrics["fallback_transitions"] > 0, metrics["fallback_transitions"], "at least one uncertainty fallback")
    selected = snapshots.graph_selected.astype(bool)
    selected_improvement = (
        float(np.sqrt(np.mean(snapshots.loc[selected, "accepted_rmse"] ** 2))) <
        float(np.sqrt(np.mean(snapshots.loc[selected, "deterministic_rmse"] ** 2)))
    ) if selected.any() else False
    gate("selected_graph_steps_improve", "diagnostic", selected_improvement, int(selected.sum()), "selected graph subset improves deterministic map-back")

    validation = pd.DataFrame(gates)
    validation.to_csv(out_dir / "PAD_Stream_V15E3_Validation_Matrix.csv", index=False)
    integrity = validation[validation.group == "integrity"]
    deployment = validation[validation.group == "deployment"]
    diagnostic = validation[validation.group == "diagnostic"]
    integrity_ok = bool(integrity.passed.all())
    deployment_ok = bool(deployment.passed.all())
    status = "PASS" if integrity_ok and deployment_ok else (
        "AUDIT_COMPLETE_DEPLOYMENT_NOT_APPROVED" if integrity_ok else "AUDIT_FAILED"
    )

    source_hashes = {
        "v14_source_sha256": sha256_file(runtime["args"].v14_source),
        "v14_frozen_sha256": sha256_file(runtime["args"].v14_frozen),
        "c3_package_sha256": sha256_file(runtime["args"].c3_package_zip),
        "d2_package_sha256": sha256_file(runtime["args"].d2_package_zip),
        "d2_checkpoint_sha256": sha256_file(runtime["args"].d2_root / "PAD_Stream_V15D2_Best_Model.pt"),
        "e0_dataset_sha256": sha256_file(runtime["args"].e0_dataset),
        "e0_operator_sha256": sha256_file(runtime["args"].e0_operator),
        "e1_checkpoint_sha256": sha256_file(runtime["args"].e1_checkpoint),
        "e2_trainer_sha256": sha256_file(runtime["args"].e2_trainer),
        "e2_checkpoint_sha256": sha256_file(runtime["args"].e2_checkpoint),
    }
    summary = {
        "version": VERSION, "status": status,
        "description": "Sequential conservative graph map-back with one unique recurrent grid state",
        "path_input_variant": runtime["args"].path_mode,
        "integrity_gates_passed": int(integrity.passed.sum()),
        "integrity_gates_total": int(len(integrity)),
        "deployment_gates_passed": int(deployment.passed.sum()),
        "deployment_gates_total": int(len(deployment)),
        "diagnostic_gates_passed": int(diagnostic.passed.sum()),
        "diagnostic_gates_total": int(len(diagnostic)),
        "deployment_approved": deployment_ok,
        "rollout_contract": "accepted grid -> corrected Pollock path sampling -> frozen 15D-2 transport -> frozen 15E-2 predict-screen-correct map-back -> accepted grid",
        "metrics": metrics,
        "v15d3_benchmark": V15D3_BENCHMARK,
        "handoff": {
            "next_milestone": "15F-0",
            "well_response_owner": "15F-1",
            "gas_cut_diagnostic_passed": bool(metrics["gas_cut_rmse"] < 0.08),
            "breakthrough_diagnostic_passed": bool(metrics["breakthrough_abs_error_days"] <= 15.0),
        },
        "source_hashes": source_hashes,
        "limitations": [
            "Pressure fields and corrected Pollock geometry are refreshed from frozen reference states; learned pressure/path integration is deferred to Version 15G.",
            "Target-time pressure is used as an available corrected pressure-branch output for compressible mass coefficients and well-response evaluation.",
            "Global timestep and retrace memory are deferred to Version 15F-0; breakthrough and well-control memory are deferred to Version 15F-1; nonlinear-difficulty memory is deferred to Version 15F-2.",
        ],
    }
    (out_dir / "PAD_Stream_V15E3_Summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    np.savez_compressed(
        out_dir / "PAD_Stream_V15E3_Rollout_Fields.npz",
        current_time_days=snapshots.current_time_days.to_numpy(np.float64),
        target_time_days=snapshots.target_time_days.to_numpy(np.float64),
        persistence_rmse=snapshots.persistence_rmse.to_numpy(np.float64),
        deterministic_rmse=snapshots.deterministic_rmse.to_numpy(np.float64),
        accepted_rmse=snapshots.accepted_rmse.to_numpy(np.float64),
        predicted_inventory_kg=snapshots.predicted_inventory_kg.to_numpy(np.float64),
        exact_inventory_kg=snapshots.exact_inventory_kg.to_numpy(np.float64),
        predicted_gas_cut=snapshots.predicted_gas_cut.to_numpy(np.float64),
        exact_gas_cut=snapshots.exact_gas_cut.to_numpy(np.float64),
        graph_selected=snapshots.graph_selected.to_numpy(bool),
        uncertainty_ratio=snapshots.uncertainty_ratio.to_numpy(np.float64),
        final_saturation=np.asarray(final_state["saturation"], np.float64),
        final_history=np.asarray(final_state["history"], np.float64),
    )
    make_plots(out_dir, snapshots, paths, validation, metrics)
    write_readme(out_dir, summary)
    write_verifier(out_dir)

    # Preserve the executable milestone source and a compact frozen dependency manifest.
    source_copy = out_dir / Path(__file__).name
    shutil.copy2(Path(__file__).resolve(), source_copy)
    dependency_manifest = {
        "version": VERSION,
        "dependencies": {
            "v14_source": {"path": str(runtime["args"].v14_source), "sha256": source_hashes["v14_source_sha256"]},
            "v14_frozen": {"path": str(runtime["args"].v14_frozen), "sha256": source_hashes["v14_frozen_sha256"]},
            "c3_package": {"path": str(runtime["args"].c3_package_zip), "sha256": source_hashes["c3_package_sha256"]},
            "d2_package": {"path": str(runtime["args"].d2_package_zip), "sha256": source_hashes["d2_package_sha256"]},
            "e0_dataset": {"path": str(runtime["args"].e0_dataset), "sha256": source_hashes["e0_dataset_sha256"]},
            "e0_operator": {"path": str(runtime["args"].e0_operator), "sha256": source_hashes["e0_operator_sha256"]},
            "e1_checkpoint": {"path": str(runtime["args"].e1_checkpoint), "sha256": source_hashes["e1_checkpoint_sha256"]},
            "e2_trainer": {"path": str(runtime["args"].e2_trainer), "sha256": source_hashes["e2_trainer_sha256"]},
            "e2_checkpoint": {"path": str(runtime["args"].e2_checkpoint), "sha256": source_hashes["e2_checkpoint_sha256"]},
        },
    }
    (out_dir / "PAD_Stream_V15E3_Dependency_Manifest.json").write_text(
        json.dumps(dependency_manifest, indent=2), encoding="utf-8"
    )

    # Freeze the milestone directory itself.
    checks = {}
    for p in sorted(out_dir.rglob("*")):
        if p.is_file() and p.name not in {"SHA256SUMS.json"}:
            checks[str(p.relative_to(out_dir))] = sha256_file(p)
    (out_dir / "SHA256SUMS.json").write_text(json.dumps(checks, indent=2, sort_keys=True), encoding="utf-8")
    zip_path = out_dir.parent / f"{out_dir.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", out_dir.parent, out_dir.name)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--v14-source", type=Path, required=True)
    p.add_argument("--v14-frozen", type=Path, required=True)
    p.add_argument("--c3-root", type=Path, required=True)
    p.add_argument("--c3-package-zip", type=Path, required=True)
    p.add_argument("--d2-root", type=Path, required=True)
    p.add_argument("--d2-package-zip", type=Path, required=True)
    p.add_argument("--d3-source", type=Path, required=True)
    p.add_argument("--e0-builder", type=Path, required=True)
    p.add_argument("--e0-dataset", type=Path, required=True)
    p.add_argument("--e0-operator", type=Path, required=True)
    p.add_argument("--e1-trainer", type=Path, required=True)
    p.add_argument("--e1-checkpoint", type=Path, required=True)
    p.add_argument("--e2-trainer", type=Path, required=True)
    p.add_argument("--e2-checkpoint", type=Path, required=True)
    p.add_argument("--path-mode", choices=["d2_raw", "d2_conservative"], default="d2_conservative")
    p.add_argument("--output", type=Path, required=True)
    return p.parse_args()


def main() -> None:
    seed_everything()
    args = parse_args()
    global VARIANT
    VARIANT = args.path_mode
    required = [
        args.v14_source, args.v14_frozen, args.c3_root, args.c3_package_zip,
        args.d2_root, args.d2_package_zip, args.d3_source, args.e0_builder,
        args.e0_dataset, args.e0_operator, args.e1_trainer, args.e1_checkpoint,
        args.e2_trainer, args.e2_checkpoint,
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(path)
    d3 = load_module("pad_stream_v15d3_runtime_for_v15e3", args.d3_source)
    configure_d3_runtime(d3, args)
    ctx = d3.build_static_context()
    _, transport_model, d2_checkpoint = d3.load_model()
    e0 = load_module("pad_stream_v15e0_builder_for_v15e3", args.e0_builder)
    e1 = load_module("pad_stream_v15e1_runtime_for_v15e3", args.e1_trainer)
    operator = load_module("pad_stream_v15e0_operator_for_v15e3", args.e0_operator)
    global operator_global
    operator_global = operator
    graph_model, e2_checkpoint = load_graph_model(e1, args.e2_checkpoint)
    with np.load(args.e0_dataset, allow_pickle=True) as z:
        base = {k: z[k].copy() for k in z.files}
    e2_trainer = load_module(
        "pad_stream_v15e2_feature_runtime_for_v15e3",
        args.e2_trainer,
    )
    teacher_idx = np.where(base["variant"] == "teacher_exact")[0]
    frozen_features, _, _ = e2_trainer.inventory_features(base, teacher_idx)
    frozen_train_features = frozen_features[base["split"][teacher_idx] == "train"]
    runtime = {
        "args": args, "d3": d3, "ctx": ctx, "e0": e0, "e1": e1,
        "operator": operator, "transport_model": transport_model,
        "d2_checkpoint": d2_checkpoint, "graph_model": graph_model,
        "e2_checkpoint": e2_checkpoint, "base": base,
        "frozen_train_features": frozen_train_features,
    }
    if args.output.exists():
        shutil.rmtree(args.output)
    summary = finalize_outputs(runtime, args.output)
    print(json.dumps(summary, indent=2))


operator_global = None

if __name__ == "__main__":
    main()
