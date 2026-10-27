"""Peng-Robinson EOS and a gas/oil flash for CO2 + reservoir-oil pseudo-components.

Used to split hydrocarbon-phase CO2 between free gas and residual oil, which
Sun et al. (2020, Fuel 278:118356) show is the dominant CO2 sink in a
depleted oil field above the minimum miscibility pressure.

Equations (Peng & Robinson 1976, Ind. Eng. Chem. Fundam. 15(1) 59-64):
    P = RT/(v - b) - a(T)/(v(v + b) + b(v - b))
    a_i(T) = 0.45724 R^2 Tc^2/Pc * alpha_i,  b_i = 0.07780 R Tc/Pc
    alpha_i = [1 + kappa_i (1 - sqrt(T/Tc))]^2
    Z^3 - (1 - B) Z^2 + (A - 3B^2 - 2B) Z - (AB - B^2 - B^3) = 0
    ln phi_i = b_i/b (Z - 1) - ln(Z - B)
               - A/(2 sqrt2 B) (2 sum_j x_j a_ij / a - b_i/b)
                 ln[(Z + (1 + sqrt2) B)/(Z + (1 - sqrt2) B)]
Checked against the paper (Part 16): eqs. 12-15 on p. 60, including the
(Z + 2.414B)/(Z - 0.414B) fugacity term.  Still to confirm against the paper:
the EOS line itself (eq. 4) and the kappa(omega) correlation, which is used
here in its widely cited 1976 form and in the 1978 extension for omega > 0.49.

Mixing: van der Waals one-fluid, a_ij = (1 - k_ij) sqrt(a_i a_j).
Flash: Michelsen (1982) tangent-plane stability test with vapour-like and
liquid-like trial phases (Wilson K start); unstable mixtures are flashed by
Rachford-Rice + successive substitution started from the stability K-values.
Near the critical point / MMP successive substitution converges slowly;
non-converged rows are flagged in FlashResult.converged.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

R = 8.314462618
SQ2 = np.sqrt(2.0)


@dataclass
class Fluid:
    names: List[str]
    Tc: np.ndarray        # K
    Pc: np.ndarray        # Pa
    omega: np.ndarray
    mw: np.ndarray        # kg/mol
    kij: np.ndarray = field(default=None)

    def __post_init__(self):
        self.Tc, self.Pc, self.omega, self.mw = (np.asarray(v, float) for v in
                                                 (self.Tc, self.Pc, self.omega, self.mw))
        n = len(self.names)
        if self.kij is None:
            self.kij = np.zeros((n, n))
        self.kij = np.asarray(self.kij, float)

    @property
    def nc(self):
        return len(self.names)

    def kappa(self):
        w = self.omega
        k76 = 0.37464 + 1.54226 * w - 0.26992 * w ** 2
        k78 = 0.379642 + 1.48503 * w - 0.164423 * w ** 2 + 0.016666 * w ** 3
        return np.where(w > 0.49, k78, k76)

    def ab(self, T):
        """Pure-component a_i(T) (Pa m^6/mol^2) and b_i (m^3/mol); T scalar or (n,)."""
        T = np.asarray(T, float)[..., None]
        alpha = (1.0 + self.kappa() * (1.0 - np.sqrt(T / self.Tc))) ** 2
        a = 0.45724 * R ** 2 * self.Tc ** 2 / self.Pc * alpha
        b = 0.07780 * R * self.Tc / self.Pc
        return a, np.broadcast_to(b, a.shape)


def load_sun2020_fwu(kij_co2_hc: float = 0.12) -> tuple[Fluid, np.ndarray]:
    """Farnsworth Unit reservoir fluid of Sun et al. (2020), Table A2, p. 13.

    Returns (Fluid, oil mole fractions).  The paper gives Tc, Pc, omega, MW and
    composition but no binary interaction coefficients; ``kij_co2_hc`` is an
    ASSUMPTION (CO2-hydrocarbon values of roughly 0.1-0.15 are typical) and is
    applied between CO2 and every hydrocarbon pseudo-component.
    """
    path = Path(__file__).with_name("data") / "sun2020_fwu_fluid.csv"
    rows = [r for r in csv.DictReader(l for l in open(path) if not l.startswith("#"))]
    names = [r["component"] for r in rows]
    fl = Fluid(names, [float(r["Tc_K"]) for r in rows],
               [float(r["Pc_atm"]) * 101325.0 for r in rows],
               [float(r["omega"]) for r in rows], [float(r["MW_g_mol"]) / 1000 for r in rows])
    i = names.index("CO2")
    k = np.zeros((fl.nc, fl.nc))
    k[i, :] = k[:, i] = kij_co2_hc
    k[i, i] = 0.0
    fl.kij = k
    z = np.array([float(r["mole_pct"]) for r in rows]) / 100.0
    z = z / z.sum()
    return fl, z


def _cubic_roots(c2, c1, c0):
    """Real roots of Z^3 + c2 Z^2 + c1 Z + c0 = 0, vectorised -> (n, 3), NaN where absent.

    Closed form (Cardano / trigonometric), one Newton polish per root."""
    c2, c1, c0 = (np.asarray(c, float) for c in (c2, c1, c0))
    p = c1 - c2 ** 2 / 3.0
    q = 2.0 * c2 ** 3 / 27.0 - c2 * c1 / 3.0 + c0
    disc = (q / 2.0) ** 2 + (p / 3.0) ** 3
    roots = np.full(c2.shape + (3,), np.nan)
    one = disc > 0
    if one.any():
        sd = np.sqrt(disc[one])
        t = np.cbrt(-q[one] / 2 + sd) + np.cbrt(-q[one] / 2 - sd)
        roots[one, 0] = t - c2[one] / 3.0
    three = ~one
    if three.any():
        pp, qq = p[three], q[three]
        m = 2.0 * np.sqrt(np.maximum(-pp / 3.0, 0.0))
        arg = np.clip(3.0 * qq / (pp * m + (m == 0)) , -1.0, 1.0)  # = (3q/2p) sqrt(-3/p)
        th = np.arccos(arg) / 3.0
        for k in range(3):
            roots[three, k] = m * np.cos(th - 2.0 * np.pi * k / 3.0) - c2[three, None][:, 0] / 3.0
    # Newton polish
    for _ in range(2):
        f = ((roots + c2[:, None]) * roots + c1[:, None]) * roots + c0[:, None]
        df = (3 * roots + 2 * c2[:, None]) * roots + c1[:, None]
        roots = roots - np.where(np.abs(df) > 1e-300, f / np.where(df == 0, 1, df), 0.0)
    return roots


def phase_props(fl: Fluid, x: np.ndarray, T, P, phase: str):
    """Z and ln(phi) for compositions x (n, nc) at T, P (scalars or (n,)).

    phase = "liquid" picks the smallest root above B, "vapor" the largest,
    "stable" the root with the lowest Gibbs energy.
    """
    x = np.atleast_2d(x)
    n = x.shape[0]
    T = np.broadcast_to(np.asarray(T, float), (n,))
    P = np.broadcast_to(np.asarray(P, float), (n,))
    a_i, b_i = fl.ab(T)                                   # (n, nc)
    aij = (1 - fl.kij)[None] * np.sqrt(a_i[:, :, None] * a_i[:, None, :])
    sum_xa = np.einsum("nj,nij->ni", x, aij)              # sum_j x_j a_ij
    a = np.einsum("ni,ni->n", x, sum_xa)
    b = np.einsum("ni,ni->n", x, b_i)
    A = a * P / (R * T) ** 2
    B = b * P / (R * T)
    roots = _cubic_roots(-(1 - B), A - 3 * B ** 2 - 2 * B, -(A * B - B ** 2 - B ** 3))
    roots = np.where(roots > B[:, None], roots, np.nan)

    def lnphi(Z):
        t = np.log((Z + (1 + SQ2) * B) / (Z + (1 - SQ2) * B))
        return (b_i / b[:, None] * (Z - 1)[:, None] - np.log(Z - B)[:, None]
                - (A / (2 * SQ2 * B))[:, None] * (2 * sum_xa / a[:, None] - b_i / b[:, None]) * t[:, None])

    Zl = np.nanmin(roots, axis=1)
    Zv = np.nanmax(roots, axis=1)
    if phase == "liquid":
        Z = Zl
    elif phase == "vapor":
        Z = Zv
    else:
        gl = (x * (lnphi(Zl) + np.log(np.clip(x, 1e-300, None)))).sum(1)
        gv = (x * (lnphi(Zv) + np.log(np.clip(x, 1e-300, None)))).sum(1)
        Z = np.where(gv < gl, Zv, Zl)
    return Z, lnphi(Z)


def molar_density(fl, x, T, P, phase="stable"):
    """mol/m^3."""
    Z, _ = phase_props(fl, x, T, P, phase)
    return np.asarray(P, float) / (Z * R * np.asarray(T, float))


def wilson_k(fl: Fluid, T, P):
    T = np.asarray(T, float)[..., None]
    P = np.asarray(P, float)[..., None]
    return fl.Pc / P * np.exp(5.373 * (1 + fl.omega) * (1 - fl.Tc / T))


def rachford_rice(z, K, iters=100):
    """Vapour fraction beta per row; values outside [0, 1] mean one phase."""
    Km1 = K - 1.0
    lo = 1.0 / (1.0 - K.max(1))
    hi = 1.0 / (1.0 - K.min(1))
    f = lambda bt: (z * Km1 / (1 + bt[:, None] * Km1)).sum(1)
    # one phase: f(0) < 0 -> all liquid, f(1) > 0 -> all vapour
    f0, f1 = f(np.zeros(len(z))), f(np.ones(len(z)))
    a, bnd = np.maximum(lo + 1e-12, 0.0), np.minimum(hi - 1e-12, 1.0)
    for _ in range(iters):
        mid = 0.5 * (a + bnd)
        fm = f(mid)
        a = np.where(fm > 0, mid, a)
        bnd = np.where(fm > 0, bnd, mid)
    beta = 0.5 * (a + bnd)
    beta = np.where(f0 < 0, 0.0, beta)
    beta = np.where(f1 > 0, 1.0, beta)
    return beta


@dataclass
class FlashResult:
    beta: np.ndarray      # vapour mole fraction
    x: np.ndarray         # liquid (oil) composition
    y: np.ndarray         # vapour (gas) composition
    converged: np.ndarray
    iterations: int
    K: np.ndarray = None


def stability(fl: Fluid, z, T, P, tol=1e-10, max_iter=500):
    """Michelsen tangent-plane test.  Returns (unstable mask, K estimate)."""
    z = np.atleast_2d(z)
    n = z.shape[0]
    Kw = wilson_k(fl, np.broadcast_to(T, (n,)), np.broadcast_to(P, (n,)))
    _, lpz = phase_props(fl, z, T, P, "stable")
    d = np.log(np.clip(z, 1e-300, None)) + lpz
    unstable = np.zeros(n, bool)
    Kbest = Kw.copy()
    best = np.zeros(n)
    for kind in ("vapor", "liquid"):
        W = z * Kw if kind == "vapor" else z / Kw
        for _ in range(max_iter):
            w = W / W.sum(1, keepdims=True)
            _, lpw = phase_props(fl, w, T, P, kind)
            Wn = np.exp(d - lpw)
            if np.abs(np.log(Wn / W)).max() < tol:
                W = Wn
                break
            W = Wn
        tpd = 1.0 - W.sum(1)                      # < 0 -> unstable
        trivial = np.abs(np.log(W / W.sum(1, keepdims=True) / z)).max(1) < 1e-4
        un = (tpd < -1e-8) & ~trivial
        w = W / W.sum(1, keepdims=True)
        Kk = w / z if kind == "vapor" else z / w
        better = un & (tpd < best)
        Kbest = np.where(better[:, None], Kk, Kbest)
        best = np.where(better, tpd, best)
        unstable |= un
    return unstable, Kbest


def flash(fl: Fluid, z, T, P, tol=1e-10, max_iter=500, K0=None) -> FlashResult:
    """Isothermal two-phase flash, vectorised over rows of z (n, nc).

    ``K0`` (n, nc) warm-starts rows from a previous solution; rows given a
    finite K0 skip the stability test (their previous state was two-phase)."""
    z = np.atleast_2d(np.asarray(z, float))
    n = z.shape[0]
    Tn = np.broadcast_to(np.asarray(T, float), (n,)).copy()
    Pn = np.broadcast_to(np.asarray(P, float), (n,)).copy()
    warm = np.zeros(n, bool) if K0 is None else np.all(np.isfinite(K0), axis=1)
    unstable = warm.copy()
    K = np.ones_like(z)
    if K0 is not None:
        K[warm] = K0[warm]
    if (~warm).any():
        u, Ks = stability(fl, z[~warm], Tn[~warm], Pn[~warm])
        unstable[~warm] = u
        K[~warm] = Ks
    conv = ~unstable
    it = 0
    for it in range(1, max_iter + 1):
        idx = np.flatnonzero(~conv)
        if idx.size == 0:
            break
        zi, Ki = z[idx], K[idx]
        beta = rachford_rice(zi, Ki)
        x = zi / (1 + beta[:, None] * (Ki - 1)); x /= x.sum(1, keepdims=True)
        y = Ki * x; y /= y.sum(1, keepdims=True)
        _, lpl = phase_props(fl, x, Tn[idx], Pn[idx], "liquid")
        _, lpv = phase_props(fl, y, Tn[idx], Pn[idx], "vapor")
        Knew = np.exp(lpl - lpv)
        err = np.abs(np.log(Knew / Ki)).max(1)
        K[idx] = Knew
        conv[idx] = err < tol
    beta = np.where(unstable, rachford_rice(z, K), 0.0)
    x = z / (1 + beta[:, None] * (K - 1)); x /= x.sum(1, keepdims=True)
    y = K * x; y /= y.sum(1, keepdims=True)
    one = ~unstable | (beta <= 0) | (beta >= 1)
    # single phase: liquid-like if T is below the Kay's-rule pseudo-critical
    # temperature sum(z_i Tc_i), vapour-like otherwise (beta = 0 or 1).
    Tpc = (z * fl.Tc).sum(1)
    Tn = np.broadcast_to(np.asarray(T, float), (n,))
    beta = np.where(one, np.where(Tn < Tpc, 0.0, 1.0), beta)
    x = np.where(one[:, None], z, x)
    y = np.where(one[:, None], z, y)
    return FlashResult(beta, x, y, conv, it, K)


def co2_fugacity(fl: Fluid, comp, T, P, phase="vapor"):
    """CO2 fugacity (Pa) of a phase with composition ``comp``."""
    i = fl.names.index("CO2")
    _, lp = phase_props(fl, comp, T, P, phase)
    return np.atleast_2d(comp)[:, i] * np.exp(lp[:, i]) * np.asarray(P, float)
