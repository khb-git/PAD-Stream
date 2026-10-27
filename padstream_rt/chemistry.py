"""Chemistry backends and the ML surrogate with a mass-balance fallback.

Design choice: every backend returns *mineral reaction extents* xi
(mol of mineral dissolved per cell over the step; negative = precipitated).
Aqueous totals then change by ``nu^T xi``, so element conservation holds by
construction for any backend, including a neural network.  A surrogate that
also predicts aqueous changes directly is checked against ``nu^T xi`` and
rejected if the mismatch exceeds a tolerance (this is the conservation residual
Guérillot & Bruyelle 2020 report as unsolved).

``ReferenceBackend`` is a small, dependency-free kinetic/equilibrium solver
(ideal activities, component totals as free activities).  It exists so that
the coupling, routing and fallback can be tested end-to-end; production runs
should implement the same ``ChemistryBackend`` interface on top of Reaktoro
or PHREEQC (speciation, activity models, CO2 solubility).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Protocol

import numpy as np

from .kinetics import mineral_rate, saturation_ratio
from .state import ChemicalSystem

LITRES_PER_M3 = 1000.0


@dataclass
class ChemInput:
    n_aq: np.ndarray        # (n, ncomp) mol in the cell's brine
    n_min: np.ndarray       # (n, nmin) mol of mineral in the cell
    v_brine: np.ndarray     # (n,) m^3
    v_bulk: float           # m^3
    area: np.ndarray        # (n, nmin) m^2 / m^3 bulk
    T: np.ndarray           # (n,) K
    P: np.ndarray           # (n,) Pa
    dt: float
    active: Optional[np.ndarray] = None  # (n, nmin) bool: minerals routed to this call

    def mask(self) -> np.ndarray:
        if self.active is None:
            return np.ones(self.n_min.shape, dtype=bool)
        return self.active

    def subset(self, rows: np.ndarray) -> "ChemInput":
        act = None if self.active is None else self.active[rows]
        return ChemInput(self.n_aq[rows], self.n_min[rows], self.v_brine[rows], self.v_bulk,
                         self.area[rows], self.T[rows], self.P[rows], self.dt, act)


class ChemistryBackend(Protocol):
    def kinetic(self, x: ChemInput) -> np.ndarray: ...
    def equilibrium(self, x: ChemInput) -> np.ndarray: ...


# ----------------------------------------------------------------------
# Reference backend
# ----------------------------------------------------------------------
class ReferenceBackend:
    """Ideal-activity reference chemistry.

    Activities = component totals in mol/L (activity coefficients = 1);
    pH = -log10 a(H+) if an "H+" component exists, otherwise ``fixed_pH``.
    Equilibrium extents are found by bisection on log10 Omega, bounded so that
    no amount becomes negative.  Minerals are swept Gauss-Seidel style.
    """

    def __init__(self, system: ChemicalSystem, fixed_pH: float = 5.0,
                 sweeps: int = 4, bisect_iter: int = 80):
        self.sys = system
        self.nu = system.nu_matrix
        self.fixed_pH = fixed_pH
        self.sweeps = sweeps
        self.iters = bisect_iter
        self.iH = system.components.index("H+") if "H+" in system.components else None

    # -- helpers -------------------------------------------------------
    def activities(self, n_aq, v_brine):
        return n_aq / (v_brine[:, None] * LITRES_PER_M3)

    def pH(self, n_aq, v_brine):
        if self.iH is None:
            return np.full(n_aq.shape[0], self.fixed_pH)
        a = self.activities(n_aq, v_brine)[:, self.iH]
        return -np.log10(np.clip(a, 1e-14, None))

    def _bounds(self, j, n_aq, n_min):
        nu = self.nu[j]
        hi = n_min[:, j].copy()
        lo = np.full(n_aq.shape[0], -np.inf)
        for i, v in enumerate(nu):
            if v < 0:
                hi = np.minimum(hi, n_aq[:, i] / -v)
            elif v > 0:
                lo = np.maximum(lo, -n_aq[:, i] / v)
        lo = np.where(np.isfinite(lo), lo, 0.0)
        return lo, np.maximum(hi, lo)

    def _log_omega(self, j, n_aq, v_brine, T):
        return np.log10(np.clip(saturation_ratio(self.sys.minerals[j], self.activities(n_aq, v_brine), T), 1e-300, None))

    def equilibrium_extent(self, j, n_aq, n_min, v_brine, T):
        lo, hi = self._bounds(j, n_aq, n_min)
        nu = self.nu[j]
        f = lambda xi: self._log_omega(j, n_aq + xi[:, None] * nu[None, :], v_brine, T)
        flo, fhi = f(lo), f(hi)
        a, b = lo.copy(), hi.copy()
        for _ in range(self.iters):
            mid = 0.5 * (a + b)
            fm = f(mid)
            right = fm < 0          # still undersaturated -> dissolve more
            a = np.where(right, mid, a)
            b = np.where(right, b, mid)
        xi = 0.5 * (a + b)
        xi = np.where(fhi <= 0, hi, xi)   # cannot reach equilibrium: exhaust
        xi = np.where(flo >= 0, lo, xi)   # supersaturated beyond availability
        return xi

    # -- interface -----------------------------------------------------
    def equilibrium(self, x: ChemInput) -> np.ndarray:
        n_aq, n_min = x.n_aq.copy(), x.n_min.copy()
        xi_tot = np.zeros_like(n_min)
        act = x.mask()
        for _ in range(self.sweeps):
            for j in range(self.sys.nmin):
                if not act[:, j].any():
                    continue
                xi = self.equilibrium_extent(j, n_aq, n_min, x.v_brine, x.T) * act[:, j]
                n_aq += xi[:, None] * self.nu[j][None, :]
                n_min[:, j] -= xi
                xi_tot[:, j] += xi
        return xi_tot

    def kinetic(self, x: ChemInput, nsub: int = 4) -> np.ndarray:
        n_aq, n_min = x.n_aq.copy(), x.n_min.copy()
        xi_tot = np.zeros_like(n_min)
        h = x.dt / nsub
        act = x.mask()
        for _ in range(nsub):
            pH = self.pH(n_aq, x.v_brine)
            for j, m in enumerate(self.sys.minerals):
                if not act[:, j].any():
                    continue
                om = saturation_ratio(m, self.activities(n_aq, x.v_brine), x.T)
                frac = np.divide(n_min[:, j], x.n_min[:, j], out=np.ones_like(n_min[:, j]),
                                 where=x.n_min[:, j] > 0)
                area = x.area[:, j] * np.clip(frac, 0.0, None) ** (2.0 / 3.0)
                xi = mineral_rate(m, area, x.T, pH, om) * x.v_bulk * h
                xi_eq = self.equilibrium_extent(j, n_aq, n_min, x.v_brine, x.T)
                # never step past equilibrium or availability
                xi = np.where(xi >= 0, np.minimum(xi, np.maximum(xi_eq, 0.0)),
                              np.maximum(xi, np.minimum(xi_eq, 0.0))) * act[:, j]
                n_aq += xi[:, None] * self.nu[j][None, :]
                n_min[:, j] -= xi
                xi_tot[:, j] += xi
        return xi_tot


# ----------------------------------------------------------------------
# Surrogate with mass-balance fallback
# ----------------------------------------------------------------------
@dataclass
class FallbackStats:
    calls: int = 0
    cells: int = 0
    rejected: int = 0
    routed: int = 0          # sent to the reference a priori by the model (stiff), not rejected
    reasons: Dict[str, int] = field(default_factory=dict)

    def add(self, reason: str, n: int):
        if n:
            self.reasons[reason] = self.reasons.get(reason, 0) + int(n)

    @property
    def fallback_rate(self) -> float:
        """Share of surrogate-handled cells rejected by the checks (a posteriori)."""
        n = self.cells - self.routed
        return self.rejected / n if n else 0.0

    @property
    def reference_rate(self) -> float:
        """Share of all cells solved by the reference (routed + rejected)."""
        return (self.rejected + self.routed) / self.cells if self.cells else 0.0


class SurrogateBackend:
    """Wrap a learned model; accept per cell only if physics checks pass.

    ``model(x: ChemInput, mode: str) -> dict`` must return ``{"xi": (n, nmin)}``
    and may return ``{"d_aq": (n, ncomp)}``.  Checks per cell:

    1. conservation: if ``d_aq`` is given, ||d_aq - nu^T xi||_inf <= rtol * scale;
    2. positivity: all aqueous and mineral amounts stay >= -atol;
    3. direction: no mineral may cross equilibrium (sign of log Omega must not
       flip by more than ``omega_tol``) - the overshoot that makes surrogate
       errors grow in time;
    4. equilibrium mode only: |log10 Omega_new| <= omega_tol for every mineral
       with remaining mass.

    Rejected cells are recomputed with ``reference`` and (optionally) appended
    to ``training_buffer`` for on-demand retraining (cf. Leal et al. 2020).
    """

    def __init__(self, model: Callable, reference: ReferenceBackend,
                 rtol: float = 1e-8, atol: float = 1e-12, omega_tol: float = 0.05,
                 keep_training_data: bool = True, speciate_fn: Optional[Callable] = None):
        self.model = model
        self.ref = reference
        self.nu = reference.nu
        self.rtol, self.atol, self.omega_tol = rtol, atol, omega_tol
        self.stats = FallbackStats()
        self.keep = keep_training_data
        self.training_buffer = []
        # Saturation indices for the overshoot / equilibrium checks.  Default:
        # the reference's own speciation (independent but as costly as a
        # PHREEQC call).  Passing the surrogate's learned speciation makes the
        # check cheap; positivity and conservation stay exact either way.
        self.speciate_fn = speciate_fn or getattr(reference, "speciate", None)

    def _check(self, x: ChemInput, out: dict, mode: str) -> np.ndarray:
        xi = np.where(x.mask(), out["xi"], 0.0)
        ok = np.all(np.isfinite(xi), axis=1)
        self.stats.add("non_finite", np.sum(~ok))
        d_aq_c = xi @ self.nu
        if "d_aq" in out:
            scale = np.maximum(np.abs(x.n_aq).max(axis=1), self.atol)
            bad = np.abs(out["d_aq"] - d_aq_c).max(axis=1) > self.rtol * scale
            self.stats.add("conservation", np.sum(bad & ok)); ok &= ~bad
        n_aq = x.n_aq + d_aq_c
        n_min = x.n_min - xi
        bad = (n_aq < -self.atol).any(axis=1) | (n_min < -self.atol).any(axis=1)
        self.stats.add("positivity", np.sum(bad & ok)); ok &= ~bad
        spec = self.speciate_fn
        if spec is not None:                       # PHREEQC or learned speciation
            LO_old = spec(x)[1]
            xn = ChemInput(np.clip(n_aq, 0, None), np.clip(n_min, 0, None), x.v_brine, x.v_bulk,
                           x.area, x.T, x.P, x.dt, x.active)
            LO_new = spec(xn)[1]
        nmin = len(self.ref.minerals) if hasattr(self.ref, "minerals") else self.ref.sys.nmin
        for j in range(nmin):
            if spec is not None:
                lo_old, lo_new = LO_old[:, j], LO_new[:, j]
            else:
                lo_old = self.ref._log_omega(j, x.n_aq, x.v_brine, x.T)
                lo_new = self.ref._log_omega(j, np.clip(n_aq, 0, None), x.v_brine, x.T)
            cross = (np.sign(lo_old) * lo_new < -self.omega_tol) & (np.abs(xi[:, j]) > 0)
            self.stats.add("overshoot", np.sum(cross & ok)); ok &= ~cross
            if mode == "equilibrium":
                present = (n_min[:, j] > self.atol) & x.mask()[:, j]
                bad = present & (np.abs(lo_new) > self.omega_tol)
                self.stats.add("not_at_equilibrium", np.sum(bad & ok)); ok &= ~bad
        return ok

    def _run(self, x: ChemInput, mode: str) -> np.ndarray:
        self.stats.calls += 1
        self.stats.cells += x.n_aq.shape[0]
        try:
            out = self.model(x, mode)
            ok = self._check(x, out, mode)
            xi = np.where(x.mask(), np.asarray(out["xi"], dtype=float), 0.0)
            routed = np.asarray(out.get("route_to_reference", np.zeros(len(ok), bool)), bool)
        except Exception:  # model failure -> everything falls back
            ok = np.zeros(x.n_aq.shape[0], dtype=bool)
            routed = np.zeros(x.n_aq.shape[0], dtype=bool)
            xi = np.zeros_like(x.n_min)
            self.stats.add("model_error", x.n_aq.shape[0])
        self.stats.routed += int(routed.sum())
        self.stats.rejected += int((~ok & ~routed).sum())
        rej = ~ok | routed
        if rej.any():
            sub = x.subset(rej)
            ref = getattr(self.ref, mode)(sub)
            xi[rej] = ref
            if self.keep:
                self.training_buffer.append((mode, sub, ref))
        return xi

    def kinetic(self, x: ChemInput) -> np.ndarray:
        return self._run(x, "kinetic")

    def equilibrium(self, x: ChemInput) -> np.ndarray:
        return self._run(x, "equilibrium")
