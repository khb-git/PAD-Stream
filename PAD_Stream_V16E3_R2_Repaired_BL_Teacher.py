#!/usr/bin/env python3
"""PAD-Stream V16E-3-R2 repaired prospective BL teacher.

Pure NumPy numerical adapter for the classical incompressible Corey/Welge
pre-breakthrough fan frozen by V16E-3-R1. This file does not train or load any
neural network and does not modify the historical Hybrid source files.
"""
from __future__ import annotations

import numpy as np

ADAPTER_ID = "V16E3_R2_STABLE_COREY_ANALYTIC_WELGE_FAN_V1"
DEFAULT_SHOCK_SCAN_NODES = 4097
DEFAULT_BISECTION_ITERATIONS = 64
DEFAULT_FAN_NODES = 4097
REQUIRED_KEYS = ("no", "nw", "swc", "sor", "mu_w", "mu_o", "krw_max", "kro_max")


class TeacherDomainError(ValueError):
    pass


def validate_params(p):
    missing = [k for k in REQUIRED_KEYS if k not in p]
    if missing:
        raise TeacherDomainError(f"Missing parameters: {missing}")
    v = {k: float(p[k]) for k in REQUIRED_KEYS}
    if not (v["no"] > 1.0 and v["nw"] > 1.0):
        raise TeacherDomainError("Corey exponents must exceed one")
    if not (0.0 <= v["swc"] < 1.0 and 0.0 <= v["sor"] < 1.0 and v["swc"] + v["sor"] < 1.0):
        raise TeacherDomainError("Invalid residual saturations")
    for key in ("mu_w", "mu_o", "krw_max", "kro_max"):
        if v[key] <= 0.0:
            raise TeacherDomainError(f"{key} must be > 0")
    return v


def _fw_s_raw(s, v):
    s = np.clip(np.asarray(s, dtype=float), 0.0, 1.0)
    lw = (v["krw_max"] / v["mu_w"]) * np.power(s, v["nw"])
    lo = (v["kro_max"] / v["mu_o"]) * np.power(1.0 - s, v["no"])
    return lw / (lw + lo)


def _dfds_raw(s, v):
    s = np.clip(np.asarray(s, dtype=float), 0.0, 1.0)
    Aw = v["krw_max"] / v["mu_w"]
    Ao = v["kro_max"] / v["mu_o"]
    lw = Aw * np.power(s, v["nw"])
    lo = Ao * np.power(1.0 - s, v["no"])
    dlw = Aw * v["nw"] * np.where(s > 0.0, np.power(s, v["nw"] - 1.0), 0.0)
    dlo = -Ao * v["no"] * np.where(s < 1.0, np.power(1.0 - s, v["no"] - 1.0), 0.0)
    total = lw + lo
    return (dlw * total - lw * (dlw + dlo)) / np.square(total)


def fractional_flow(Sw, p):
    v = validate_params(p)
    span = 1.0 - v["swc"] - v["sor"]
    s = (np.asarray(Sw, dtype=float) - v["swc"]) / span
    return _fw_s_raw(s, v)


def dfw_dsw(Sw, p):
    v = validate_params(p)
    span = 1.0 - v["swc"] - v["sor"]
    s = (np.asarray(Sw, dtype=float) - v["swc"]) / span
    return _dfds_raw(s, v) / span


def welge_shock(p, scan_nodes=DEFAULT_SHOCK_SCAN_NODES,
                 bisection_iterations=DEFAULT_BISECTION_ITERATIONS):
    """Physical Welge tangent from analytic Corey fractional-flow physics."""
    v = validate_params(p)
    scan_nodes = int(scan_nodes)
    bisection_iterations = int(bisection_iterations)
    if scan_nodes < 17 or bisection_iterations < 20:
        raise TeacherDomainError("Insufficient shock resolution")
    s_scan = np.linspace(1.0e-12, 1.0 - 1.0e-12, scan_nodes, dtype=float)
    fw = _fw_s_raw(s_scan, v)
    g = _dfds_raw(s_scan, v) - fw / s_scan
    crossings = np.where((g[:-1] >= 0.0) & (g[1:] <= 0.0))[0]
    if crossings.size == 0:
        raise TeacherDomainError("No physical Welge tangent root found")
    roots = []
    for idx in crossings.tolist():
        lo = float(s_scan[idx]); hi = float(s_scan[idx + 1])
        for _ in range(bisection_iterations):
            mid = 0.5 * (lo + hi)
            gm = float(_dfds_raw(mid, v) - _fw_s_raw(mid, v) / mid)
            if gm > 0.0:
                lo = mid
            else:
                hi = mid
        roots.append(0.5 * (lo + hi))
    span = 1.0 - v["swc"] - v["sor"]
    secants = np.asarray([float(_fw_s_raw(root, v)) / (span * root) for root in roots])
    selected = int(np.argmax(secants))
    s_star = float(roots[selected])
    Sw_star = v["swc"] + span * s_star
    fw_star = float(_fw_s_raw(s_star, v))
    characteristic_speed = float(_dfds_raw(s_star, v) / span)
    chord_speed = float(fw_star / (Sw_star - v["swc"]))
    return {
        "Sw_star": float(Sw_star), "fw_star": fw_star, "s_star": s_star,
        "characteristic_speed": characteristic_speed, "chord_speed": chord_speed,
        "tD_BT": float(1.0 / characteristic_speed), "root_count": int(len(roots)),
        "all_roots_s": [float(x) for x in roots],
        "all_secant_speeds": [float(x) for x in secants],
        "scan_nodes": scan_nodes, "bisection_iterations": bisection_iterations,
    }


def fan_profile_from_shock(p, xi, shock, fan_nodes=DEFAULT_FAN_NODES):
    """Construct a fan using a pre-qualified shock state."""
    v = validate_params(p)
    xi = np.asarray(xi, dtype=float)
    if xi.ndim != 1 or xi.size < 2 or not np.all(np.isfinite(xi)):
        raise TeacherDomainError("xi must be a finite one-dimensional grid")
    if np.any(np.diff(xi) <= 0.0) or xi[0] < 0.0 or xi[-1] > 1.0:
        raise TeacherDomainError("xi must be strictly increasing in [0,1]")
    fan_nodes = int(fan_nodes)
    if fan_nodes < 17:
        raise TeacherDomainError("Insufficient fan resolution")
    span = 1.0 - v["swc"] - v["sor"]
    s_branch = np.linspace(float(shock["s_star"]), 1.0, fan_nodes, dtype=float)
    xi_branch = (_dfds_raw(s_branch, v) / span) / float(shock["characteristic_speed"])
    Sw_branch = v["swc"] + span * s_branch
    x = xi_branch[::-1].copy(); y = Sw_branch[::-1].copy()
    x[0] = 0.0; y[0] = 1.0 - v["sor"]
    x[-1] = 1.0; y[-1] = float(shock["Sw_star"])
    if np.any(np.diff(x) < -1.0e-12):
        raise TeacherDomainError("Characteristic fan branch is not monotone")
    keep = np.concatenate(([True], np.diff(x) > 0.0))
    x = x[keep]; y = y[keep]
    if x.size < 2 or x[0] != 0.0 or x[-1] != 1.0:
        raise TeacherDomainError("Fan does not cover normalized domain")
    return np.interp(xi, x, y).astype(float)


def fan_profile(p, xi, fan_nodes=DEFAULT_FAN_NODES,
                shock_scan_nodes=DEFAULT_SHOCK_SCAN_NODES):
    shock = welge_shock(p, scan_nodes=shock_scan_nodes)
    return fan_profile_from_shock(p, xi, shock, fan_nodes=fan_nodes), shock

def teacher_targets(p, clock_fractions, xi, fan_nodes=DEFAULT_FAN_NODES,
                    shock_scan_nodes=DEFAULT_SHOCK_SCAN_NODES):
    fractions = np.asarray(clock_fractions, dtype=float)
    if fractions.ndim != 1 or fractions.size == 0 or np.any(~np.isfinite(fractions)):
        raise TeacherDomainError("Invalid clock fractions")
    if np.any(fractions <= 0.0) or np.any(fractions >= 1.0):
        raise TeacherDomainError("clock fractions must satisfy 0 < fraction < 1")
    fan, shock = fan_profile(p, xi, fan_nodes=fan_nodes, shock_scan_nodes=shock_scan_nodes)
    tD = fractions / shock["characteristic_speed"]
    targets = np.broadcast_to(fan[None, :], (fractions.size, fan.size)).copy()
    return {
        "Sw_fan_teacher": targets,
        "tD": tD,
        "xD_star": fractions.copy(),
        "Sw_star": np.full_like(fractions, shock["Sw_star"], dtype=float),
        "shock": shock,
    }
