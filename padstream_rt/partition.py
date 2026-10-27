"""CO2 partitioning between free gas, residual oil and brine (depleted oil field).

v0.1 model assumptions (stated in docs/REACTIVE_TRANSPORT_DESIGN.md §7):
* Residual oil is immobile.  PAD-Stream transports one free CO2 phase; this
  module splits the CO2 present in each cell between that phase, the oil left
  in the cell and the brine, at local equilibrium (equal CO2 fugacity).
* Oil swelling and the oil's volume change are not fed back to saturations
  yet (needs a three-phase flow solver).
* Gas/oil equilibrium: Peng-Robinson flash (pvt.py) with the Farnsworth fluid
  of Sun et al. (2020, Table A2) or any user fluid.  Brine: PHREEQC
  (phreeqc_backend.py), equilibrated with CO2 at the hydrocarbon-phase fugacity.
* Water in the gas and hydrocarbons in the brine are neglected.

Conservation: CO2 is only moved between the hydrocarbon pool and the brine's
total carbon, so cell CO2 is conserved exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .pvt import Fluid, flash, phase_props


@dataclass
class HydrocarbonState:
    """Per-cell hydrocarbon inventory (moles).

    n_hc[:, i] are moles of each fluid component in the gas + oil phases of a
    cell; the CO2 entry is the CO2 not dissolved in brine.
    """

    fluid: Fluid
    n_hc: np.ndarray            # (ncell, nc)

    @property
    def i_co2(self):
        return self.fluid.names.index("CO2")


@dataclass
class PartitionResult:
    co2_gas: np.ndarray         # mol CO2 in free gas
    co2_oil: np.ndarray         # mol CO2 dissolved in oil
    co2_brine_delta: np.ndarray # mol CO2 moved into brine this call (negative = exsolved)
    vapor_fraction: np.ndarray
    fugacity: np.ndarray        # Pa
    iterations: int


def hc_co2_fugacity(fl: Fluid, n_hc, T, P, K0=None):
    """CO2 fugacity of the hydrocarbon system and its phase split."""
    tot = n_hc.sum(1)
    z = n_hc / np.where(tot > 0, tot, 1.0)[:, None]
    r = flash(fl, z, T, P, K0=K0)
    i = fl.names.index("CO2")
    two = (r.beta > 0) & (r.beta < 1)
    ref = np.where(two[:, None], r.y, z)                     # fugacities equal in both phases
    phase = np.where(two | (r.beta >= 1), "vapor", "liquid")
    f = np.empty(len(z))
    for ph in ("vapor", "liquid"):
        m = phase == ph
        if m.any():
            Tm = np.broadcast_to(T, (len(z),))[m]; Pm = np.broadcast_to(P, (len(z),))[m]
            _, lp = phase_props(fl, ref[m], Tm, Pm, ph)
            f[m] = ref[m, i] * np.exp(lp[:, i]) * Pm
    return f, r, tot


def equilibrate_co2(hc: HydrocarbonState, backend, n_aq, v_brine, T, P, cells=None,
                    max_iter=30, rtol=1e-6, relax=1.0) -> PartitionResult:
    """Equilibrate CO2 between the hydrocarbon phases and brine in ``cells``.

    Updates ``hc.n_hc`` and ``n_aq`` (brine element totals, column "C") in place.
    """
    fl = hc.fluid
    ic = hc.i_co2
    ncell = n_aq.shape[0]
    cells = np.arange(ncell) if cells is None else np.asarray(cells)
    jC = backend.elements.index("C")
    T = np.broadcast_to(np.asarray(T, float), (ncell,))
    P = np.broadcast_to(np.asarray(P, float), (ncell,))
    moved = np.zeros(ncell)
    active = cells[hc.n_hc[cells].sum(1) > 0]
    Kwarm = np.full((ncell, fl.nc), np.nan)
    it = 0
    for it in range(1, max_iter + 1):
        if active.size == 0:
            break
        f, r, _ = hc_co2_fugacity(fl, hc.n_hc[active], T[active], P[active], K0=Kwarm[active])
        two = (r.beta > 0) & (r.beta < 1)
        Kwarm[active] = np.where(two[:, None], r.K, np.nan)
        dn = backend.co2_saturation(n_aq[active], v_brine[active], T[active], P[active], f)
        # cannot dissolve more CO2 than the hydrocarbon pool holds, nor exsolve more than the brine C
        dn = np.clip(relax * dn, -n_aq[active, jC], hc.n_hc[active, ic])
        hc.n_hc[active, ic] -= dn
        n_aq[active, jC] += dn
        moved[active] += dn
        scale = np.maximum(np.abs(n_aq[active, jC]), 1e-12)
        done = np.abs(dn) < rtol * scale
        active = active[~done]
    sel = cells
    f, r, tot = hc_co2_fugacity(fl, hc.n_hc[sel], T[sel], P[sel], K0=Kwarm[sel])
    co2_gas = np.zeros(ncell); co2_oil = np.zeros(ncell); beta = np.zeros(ncell); fug = np.zeros(ncell)
    co2_gas[sel] = r.beta * tot * r.y[:, ic]
    co2_oil[sel] = (1 - r.beta) * tot * r.x[:, ic]
    beta[sel] = r.beta
    fug[sel] = f
    return PartitionResult(co2_gas, co2_oil, moved, beta, fug, it)
