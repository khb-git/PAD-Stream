#!/usr/bin/env python3
"""PAD-Stream V16E-9 reusable Hybrid BL-DP transport adapter.

Pure NumPy state/coordinate adapter. It does not import TensorFlow, load a
checkpoint, train a model, or perform grid map-back.
"""
from __future__ import annotations

import math
from typing import Mapping

import numpy as np

ADAPTER_ID = "V16E9_HYBRID_POLLOCK_FAN_ADAPTER_V1"
FEATURES10 = ("no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star")
FEATURES12 = ("no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max", "tD", "xD_star", "Sw_star")
HYBRID12_KRW_BOUNDS = (0.05, 0.80)
HYBRID12_KRO_BOUNDS = (0.30, 0.80)
FIXED_ENDPOINT = 0.8
IDENTITY_TOL = 1.0e-12


class AdapterDomainError(ValueError):
    pass


def _f(x, name: str) -> float:
    try:
        v = float(x)
    except Exception as exc:
        raise AdapterDomainError(f"{name} is not numeric") from exc
    if not math.isfinite(v):
        raise AdapterDomainError(f"{name} must be finite")
    return v


def route_branch(*, endpoints_explicit: bool, krw_max=None, kro_max=None,
                 identity_tol: float = IDENTITY_TOL) -> str:
    """Return HYBRID10, HYBRID12, or EXACT_FALLBACK under the frozen E7 rule."""
    if not endpoints_explicit:
        return "EXACT_FALLBACK"
    try:
        krw = _f(krw_max, "krw_max")
        kro = _f(kro_max, "kro_max")
    except AdapterDomainError:
        return "EXACT_FALLBACK"
    if abs(krw - FIXED_ENDPOINT) <= identity_tol and abs(kro - FIXED_ENDPOINT) <= identity_tol:
        return "HYBRID10"
    if HYBRID12_KRW_BOUNDS[0] <= krw <= HYBRID12_KRW_BOUNDS[1] and HYBRID12_KRO_BOUNDS[0] <= kro <= HYBRID12_KRO_BOUNDS[1]:
        return "HYBRID12"
    return "EXACT_FALLBACK"


def physical_params_from_row(row) -> dict[str, float]:
    """Convert the frozen E4 physical_parameters row into named physics values."""
    a = np.asarray(row, dtype=float)
    if a.shape != (11,) or not np.all(np.isfinite(a)):
        raise AdapterDomainError("physical_parameters row must be finite with shape (11,)")
    names = ("no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "k_mD", "h_ft", "krw_max", "kro_max")
    p = {k: float(v) for k, v in zip(names, a.tolist())}
    if not (p["no"] > 1.0 and p["nw"] > 1.0):
        raise AdapterDomainError("Corey exponents must exceed one")
    if not (0.0 <= p["swc"] < 1.0 and 0.0 <= p["sor"] < 1.0 and p["swc"] + p["sor"] < 1.0):
        raise AdapterDomainError("invalid residual saturation state")
    if p["mu_w"] <= 0.0 or p["mu_o"] <= 0.0 or p["phi"] <= 0.0:
        raise AdapterDomainError("fluid/porosity values must be positive")
    return p


def teacher_params(p: Mapping[str, float]) -> dict[str, float]:
    keys = ("no", "nw", "swc", "sor", "mu_w", "mu_o", "krw_max", "kro_max")
    return {k: _f(p[k], k) for k in keys}


def synthetic_roundtrip_state(*, tD: float, characteristic_speed: float, Sw_star: float,
                              tau_end: float = 1.0) -> dict[str, float]:
    """Frozen E8 dimensionless roundtrip with tau_end=1 by default."""
    td = _f(tD, "tD")
    speed = _f(characteristic_speed, "characteristic_speed")
    swstar = _f(Sw_star, "Sw_star")
    te = _f(tau_end, "tau_end")
    if not (td > 0.0 and speed > 0.0 and te > 0.0):
        raise AdapterDomainError("tD, characteristic speed and tau_end must be positive")
    elapsed = td * te
    tau_star = elapsed * speed
    xstar = tau_star / te
    if not (0.0 < xstar < 1.0):
        raise AdapterDomainError("state is not pre-breakthrough: xD_star must be in (0,1)")
    return {
        "tau_end": te,
        "elapsed_time": elapsed,
        "tD": td,
        "tau_star": tau_star,
        "xD_star": xstar,
        "Sw_star": swstar,
        "characteristic_speed": speed,
    }


def physical_time_state(*, elapsed_time: float, tau_end: float, characteristic_speed: float,
                        Sw_star: float) -> dict[str, float]:
    t = _f(elapsed_time, "elapsed_time")
    te = _f(tau_end, "tau_end")
    speed = _f(characteristic_speed, "characteristic_speed")
    swstar = _f(Sw_star, "Sw_star")
    if not (t > 0.0 and te > 0.0 and speed > 0.0):
        raise AdapterDomainError("elapsed time, tau_end and characteristic speed must be positive")
    td = t / te
    tau_star = t * speed
    xstar = tau_star / te
    if not (0.0 < xstar < 1.0):
        raise AdapterDomainError("state is not pre-breakthrough")
    return {
        "tau_end": te, "elapsed_time": t, "tD": td, "tau_star": tau_star,
        "xD_star": xstar, "Sw_star": swstar, "characteristic_speed": speed,
    }


def conditioning_vector(branch: str, p: Mapping[str, float], state: Mapping[str, float]) -> np.ndarray:
    branch = str(branch).upper()
    if branch not in {"HYBRID10", "HYBRID12"}:
        raise AdapterDomainError("conditioning is available only for HYBRID10/HYBRID12")
    common = [
        _f(p["no"], "no"), _f(p["nw"], "nw"), _f(p["swc"], "swc"),
        _f(p["sor"], "sor"), _f(p["mu_w"], "mu_w"), _f(p["mu_o"], "mu_o"),
        _f(p["phi"], "phi"),
    ]
    tail = [_f(state["tD"], "tD"), _f(state["xD_star"], "xD_star"), _f(state["Sw_star"], "Sw_star")]
    if branch == "HYBRID10":
        if abs(_f(p["krw_max"], "krw_max") - FIXED_ENDPOINT) > IDENTITY_TOL or abs(_f(p["kro_max"], "kro_max") - FIXED_ENDPOINT) > IDENTITY_TOL:
            raise AdapterDomainError("HYBRID10 requires explicit fixed 0.8/0.8 endpoints")
        values = common + tail
    else:
        krw = _f(p["krw_max"], "krw_max"); kro = _f(p["kro_max"], "kro_max")
        if not (HYBRID12_KRW_BOUNDS[0] <= krw <= HYBRID12_KRW_BOUNDS[1] and HYBRID12_KRO_BOUNDS[0] <= kro <= HYBRID12_KRO_BOUNDS[1]):
            raise AdapterDomainError("HYBRID12 endpoints outside frozen bounds")
        values = common + [krw, kro] + tail
    return np.asarray(values, dtype=np.float32)


def project_fan_to_pollock_nodes(*, tau_nodes, state: Mapping[str, float], fan_xi, fan_sw,
                                swc: float) -> np.ndarray:
    tau = np.asarray(tau_nodes, dtype=float)
    xi = np.asarray(fan_xi, dtype=float)
    sw = np.asarray(fan_sw, dtype=float)
    if tau.ndim != 1 or xi.ndim != 1 or sw.ndim != 1 or xi.shape != sw.shape:
        raise AdapterDomainError("tau_nodes and fan arrays must be one-dimensional")
    if xi.size < 2 or np.any(np.diff(xi) <= 0.0) or xi[0] != 0.0 or xi[-1] != 1.0:
        raise AdapterDomainError("fan_xi must be strictly increasing from 0 to 1")
    if np.any(~np.isfinite(tau)) or np.any(~np.isfinite(sw)) or np.any(np.diff(tau) < 0.0):
        raise AdapterDomainError("nonfinite/nonmonotone projection arrays")
    te = _f(state["tau_end"], "tau_end")
    ts = _f(state["tau_star"], "tau_star")
    if tau.size < 2 or abs(float(tau[0])) > 1e-14 or abs(float(tau[-1]) - te) > 1e-12:
        raise AdapterDomainError("tau_nodes must span [0,tau_end]")
    out = np.full(tau.shape, _f(swc, "swc"), dtype=float)
    invaded = tau <= ts
    eta = np.clip(tau[invaded] / ts, 0.0, 1.0)
    out[invaded] = np.interp(eta, xi, sw)
    return out
