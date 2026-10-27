"""Operator-split reactive step that plugs into the PAD-Stream time loop.

One call per PAD-Stream global step, after the pressure / saturation update
(V15-SG3..SG7 or the POSTV16 AV4 coupled fixed point):

    1. transport  aqueous totals along streamlines (TransferOperator, upwind)
    2. map-back   PV*-weighted, conservative, positivity preserving
    3. route      every cell a priori by Damkohler (damkohler.route)
    4. chemistry  SKIP: nothing | KINETIC / EQUILIBRIUM: backend (ML + fallback)
    5. rock       mineral volume -> porosity -> permeability (KC / VP / learned)
    6. feedback   rebuild PV* (porosity) and report whether streamlines must be
                  retraced (permeability) before the next pressure solve

A ledger checks component conservation every step:
    inventory(t+dt) - inventory(t) = inflow - outflow   (to round-off)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np

from .chemistry import ChemInput, ReferenceBackend
from .damkohler import Regime, RoutingConfig, cell_regime, reactive_area, route
from .petrophysics import needs_retrace, update_permeability, update_porosity
from .state import ReactiveState
from .transfer import TransferOperator, advect_along_streamlines


@dataclass
class StepReport:
    regime_counts: Dict[str, int]
    mass_balance_error: np.ndarray       # (ncomp,) relative
    outflow: np.ndarray
    inflow: np.ndarray
    transport_substeps: int
    max_rel_dk: float
    retrace: bool
    perm_fallback_cells: int
    extra: Dict = field(default_factory=dict)


def reactive_step(state: ReactiveState, op: TransferOperator, backend, dt: float,
                  brine_fractional_flow: np.ndarray, c_inlet: Optional[np.ndarray] = None,
                  routing: RoutingConfig = RoutingConfig(), perm_law="kozeny_carman",
                  retrace_tol: float = 0.02, pH_fn=None, hydrocarbons=None,
                  co2_backend=None, spec_fn=None, chem_order=("kinetic", "equilibrium"),
                  chem_substeps: int = 1) -> StepReport:
    """One reactive step.  If ``hydrocarbons`` (partition.HydrocarbonState) is
    given, CO2 is first equilibrated between free gas, residual oil and brine
    with ``co2_backend`` (a PhreeqcBackend; defaults to ``backend`` or its
    reference).  The CO2 moved into brine is reported in
    ``extra['co2_to_brine']`` and accounted for in the mass ledger; the caller
    removes it from PAD-Stream's free-phase CO2."""
    sys_ = state.system
    inv0 = state.component_inventory()

    # 1-2. transport + map-back ----------------------------------------
    c_cv = op.to_cv(state.total_aq)
    sb_cv = op.to_cv(state.brine_saturation)
    fb_cv = op.to_cv(np.asarray(brine_fractional_flow, float))
    c_new, out, inn, nsub = advect_along_streamlines(op, c_cv, sb_cv, fb_cv, dt, c_inlet)
    state.total_aq = op.to_grid(c_new, state.total_aq)

    # 2b. CO2 gas / oil / brine equilibrium (depleted oil field) ---------
    vb = state.brine_volume()
    n_aq = state.total_aq * vb[:, None]
    co2_in = np.zeros(sys_.ncomp)
    part = None
    if hydrocarbons is not None:
        from .partition import equilibrate_co2
        cb = co2_backend or (backend.ref if hasattr(backend, "ref") else backend)
        cells = np.flatnonzero((hydrocarbons.n_hc.sum(1) > 0) & (vb > 0))
        part = equilibrate_co2(hydrocarbons, cb, n_aq, vb, state.temperature, state.pressure, cells)
        co2_in[sys_.components.index("C")] = part.co2_brine_delta.sum()
        state.total_aq = np.divide(n_aq, vb[:, None], out=state.total_aq.copy(), where=vb[:, None] > 0)

    # 3. a priori routing ----------------------------------------------
    n_min = state.mineral_moles()
    if pH_fn is None:
        chem = backend.ref if hasattr(backend, "ref") else backend
        if hasattr(chem, "speciate"):          # PHREEQC: needs T and P
            pH_fn = lambda a, v: chem.pH(a, v, state.temperature, state.pressure)
        elif hasattr(chem, "pH"):
            pH_fn = chem.pH
    # spec_fn(n_aq, v_brine) -> (pH, SI) enables the saturation-aware
    # Damkohler number (precipitating minerals limited by aqueous supply)
    si = None
    if spec_fn is not None:
        pH, si = spec_fn(n_aq, vb)
    else:
        pH = pH_fn(n_aq, vb) if pH_fn is not None else 5.0
    state.regime = route(state, op.residence_time, dt, routing, pH=pH, previous=state.regime, si=si)

    # 4. chemistry on routed cells --------------------------------------
    area = reactive_area(state)
    # Sequential split of the routed chemistry.  Default: kinetic pairs first,
    # then the EQUILIBRIUM pairs re-equilibrate with what the kinetics released,
    # so the step ends at equilibrium for them.  (v0.3.0 ran equilibrium first;
    # in the carbonate-bearing Argenta that left Mg from chlorite unbuffered and
    # missed 66-87 % of the mineral change against full kinetics, 27 Oct 2026.)
    # ``chem_substeps`` > 1 alternates the sequence over dt / chem_substeps.
    code_of = {"equilibrium": Regime.EQUILIBRIUM, "kinetic": Regime.KINETIC}
    h = dt / chem_substeps
    for _ in range(chem_substeps):
        for method in chem_order:
            act = (state.regime == code_of[method]) & (vb > 0)[:, None]
            rows = act.any(axis=1)
            if rows.any():
                x = ChemInput(n_aq[rows], n_min[rows], vb[rows], state.geom.cell_volume,
                              area[rows], state.temperature[rows], state.pressure[rows], h,
                              act[rows])
                xi_r = np.where(act[rows], getattr(backend, method)(x), 0.0)
                n_aq[rows] += xi_r @ sys_.nu_matrix
                n_min[rows] -= xi_r

    # 5. rock update ------------------------------------------------------
    vm = np.array([m.molar_volume for m in sys_.minerals])
    vf_old = state.mineral_vf.copy()
    state.mineral_vf = np.clip(n_min, 0.0, None) * vm[None, :] / state.geom.cell_volume
    phi_prev = state.porosity.copy()
    state.porosity = update_porosity(state, vf_old)
    vb_new = state.brine_volume()
    state.total_aq = np.divide(n_aq, vb_new[:, None], out=state.total_aq.copy(),
                               where=vb_new[:, None] > 0)
    perm_old = state.perm.copy()
    state.perm, fb = update_permeability(state, perm_law, phi_prev=phi_prev)

    # 6. feedback -------------------------------------------------------
    op.rebuild_volumes(state.porosity * state.geom.cell_volume)
    inv1 = state.component_inventory()
    scale = np.maximum(np.abs(inv0), 1e-30)
    err = (inv1 - inv0 - (inn - out) - co2_in) / scale
    cell_reg = cell_regime(state.regime)
    counts = {r.name: int(np.sum(cell_reg == r)) for r in Regime}
    per_mineral = {m.name: {r.name: int(np.sum(state.regime[:, j] == r)) for r in Regime}
                   for j, m in enumerate(sys_.minerals)}
    stats = getattr(backend, "stats", None)
    return StepReport(counts, err, out, inn, nsub,
                      float(np.max(np.abs(state.perm / perm_old - 1.0))),
                      needs_retrace(perm_old, state.perm, retrace_tol), int(fb.sum()),
                      {"per_mineral": per_mineral,
                       "co2_to_brine": None if part is None else part.co2_brine_delta,
                       "co2_gas": None if part is None else part.co2_gas,
                       "co2_oil": None if part is None else part.co2_oil,
                       "fallback_rate": getattr(stats, "fallback_rate", None),
                       "fallback_reasons": dict(getattr(stats, "reasons", {}) or {})})
