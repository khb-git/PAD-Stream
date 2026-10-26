# PAD-Stream reactive transport: interface design (`padstream_rt` v0.1)

Branch `rt-interface`. This document ties the code to the gap statement in the literature review (Part 12.3). The claim numbers below follow the 12.2 table.

## 1. What is new and where it lives

| Gap element (12.3) | Module | Status |
|---|---|---|
| (i) Per-cell, per-mineral Damköhler from streamline time-of-flight, used **before** chemistry to route to equilibrium / kinetic / skip | `damkohler.py` | Implemented and tested |
| (ii) ML surrogate guarded by a mass-balance fallback | `chemistry.py` (`SurrogateBackend`) | Implemented and tested; the model itself is not yet trained |
| (ii) Evolving porosity and permeability; learned φ→k guarded by Kozeny–Carman | `petrophysics.py` | Implemented and tested |
| (ii) Conservative 3D streamline framework for many aqueous components | `transfer.py` | Implemented and tested (replaces the per-component LP for aqueous species) |
| (iii) Depleted oil reservoir, mineral + asphaltene | `state.py` hooks (residual oil via brine saturation; asphaltene as an extra solid phase) | Assumptions documented (§7); asphaltene kinetics not implemented |

How this differs from the closest prior work (review 12.10):

- **Coatléven et al. 2026** switch a posteriori: they solve, test a Gibbs residual, and replay. We classify before solving, from transport.
- **Yao & Battiato 2025** use an a priori dimensionless-number test, but to switch model *scale*. We use it to switch the *chemistry treatment*, and per mineral.
- **Guérillot & Bruyelle 2020** switch at a fixed time and are not mass conservative. Here conservation holds by construction: backends return mineral extents ξ, and aqueous totals change by νᵀξ. Any surrogate output that breaks conservation, positivity or the direction of approach to equilibrium is rejected cell by cell.

## 2. Step loop

```
PAD-Stream global step n  (existing: SG3 pressure -> SG4 fluxes -> SG5/SG6 trace+TOF -> saturation/AV4 fixed point)
        |
        v
reactive_step(state, op, backend, dt, f_brine, c_inlet)
  1. transport   aqueous totals on 1078 x 200 CVs, explicit upwind, CFL substeps
  2. map-back    PV*-weighted mean -> grid   (exact, conservative, positivity preserving)
  3. route       Regime[cell, mineral] from Da_tau and Da_dt   (no chemistry evaluated)
  4. chemistry   EQUILIBRIUM minerals -> backend.equilibrium ; KINETIC -> backend.kinetic ; SKIP -> none
  5. rock        vf -> phi -> k  (KC | Verma-Pruess | learned+guard)
  6. feedback    op.rebuild_volumes(phi)  ;  StepReport.retrace = max|dk/k| > 2 %
        |
        v
if retrace: transmissibilities_field_units(k) -> SG3 pressure -> SG5/SG6 -> new TransferOperator
```

## 3. State schema (`ReactiveState`, flattened C order, SI units)

| Field | Shape | Units | Source |
|---|---|---|---|
| `porosity`, `porosity0` | (n,) | – | SG1 (0.20) |
| `perm`, `perm0` | (n, 3) | m² | `io.load_sgsim_perm` (kz = 0.1 k, as SG2) |
| `brine_saturation` | (n,) | – | PAD-Stream saturation: S_b = 1 − S_g − S_or |
| `total_aq` | (n, ncomp) | mol per m³ brine | component totals (linear under transport) |
| `mineral_vf` | (n, nmin) | m³ per m³ bulk | initial mineralogy (Mt. Simon table) |
| `temperature`, `pressure` | (n,) | K, Pa | isothermal for now; pressure from SG3 (psi × 6894.76) |
| `regime` | (n, nmin) | int8 | `Regime.SKIP/KINETIC/EQUILIBRIUM` |

Conservation identity used in every ledger check:

    inventory = Σ_cells V_brine · total_aq + Σ_cells n_min · ν

Dissolution and precipitation leave the inventory unchanged; transport changes it only by inflow minus outflow.

## 4. Interfaces

```python
TransferOperator(geom, StreamlineBundle, cell_pore_volume)
    .to_cv(cell_values) -> (nsl, ncv, ...)
    .to_grid(cv_values, cell_values) -> (ncell, ...)
    .rebuild_volumes(cell_pore_volume)            # after porosity change, no retrace
    .residence_time                                # (ncell,) s, inf if no streamline
advect_along_streamlines(op, c_cv, sb_cv, fb_cv, dt, c_inlet) -> c, outflow, inflow, nsub

route(state, residence_time, dt, RoutingConfig, pH, previous) -> (ncell, nmin) int8

class ChemistryBackend(Protocol):
    def equilibrium(self, x: ChemInput) -> xi  # (n, nmin) mol dissolved
    def kinetic(self, x: ChemInput) -> xi
ReferenceBackend(system)                       # ideal-activity reference (tests, fallback)
SurrogateBackend(model, reference, rtol, atol, omega_tol)
    model(x, mode) -> {"xi": ..., optional "d_aq": ...}
    .stats.fallback_rate, .stats.reasons, .training_buffer

update_permeability(state, "kozeny_carman" | "verma_pruess" | LearnedPermeability(...))
transmissibilities_field_units(perm, geom, mu_cp) -> tx, ty, tz   # mD*ft/cP, SG2 shapes
reactive_step(...) -> StepReport(regime_counts, mass_balance_error, retrace, extra[per_mineral, fallback_rate])
```

## 5. Algorithms

**PV\* transfer.** The pore volume swept by a CV is q·Δτ. Per cell, CV volumes are rescaled so that they sum to the grid pore volume: PV\* = PV·V_p/ΣPV. With this rescaling:

- grid→CV followed by CV→grid is the identity;
- the map-back is a convex combination, so it never creates negative concentrations;
- moles are identical in both spaces, to round-off.

This replaces one HiGHS LP per component with a single sparse matrix that is reused for every component. The diagnostic `capacity_ratio` shows how far the raw bundle volume is from the grid pore volume.

**Damköhler routing.** For each cell and mineral:

- Da_τ = k(T, pH) · a · τ_res / (φ S_b c_eq)
- Da_dt = k · a · Δt / (φ S_b c_eq)

The residence time is τ_res = V_p / Σ q over the streamlines crossing the cell. The routing rule is:

- **EQUILIBRIUM** if Da_τ ≥ Da_eq or Da_dt ≥ Da_eq;
- **SKIP** if Da_dt ≤ Da_skip;
- **KINETIC** otherwise.

A tolerance band (α₁) adds hysteresis so regimes do not flip back and forth. Active zones are dilated by `buffer_cells` (α₂), which is the same device as Yao & Battiato's Eqs. 17–19. Stagnant cells, with no streamline, are routed by Da_dt only.

**Surrogate acceptance**, checked per cell:

1. finite output;
2. ‖d_aq − νᵀξ‖∞ ≤ rtol·scale;
3. all amounts ≥ −atol;
4. no mineral crosses equilibrium by more than `omega_tol` in log Ω;
5. in equilibrium mode, |log Ω| ≤ `omega_tol` for every mineral still present.

Rejected cells are recomputed by the reference backend and stored in `training_buffer` for on-demand retraining.

**Learned φ→k guard.** The learned model is replaced by Kozeny–Carman when any of these holds:

- the porosity is outside the training range;
- the output is not finite;
- the output moves opposite to the porosity change.

The result is also clipped to [10⁻³, 10³]·k₀.

## 6. Verification on this branch

- `pytest -q` passes 11 tests:
  - transfer round trip and conservation;
  - upwind conservation and positivity;
  - routing limits and dilation;
  - reference equilibrium and no kinetic overshoot;
  - surrogate accept/reject, including the conservation leak;
  - KC, VP and the learned guard;
  - transmissibilities equal to the SG2 formula;
  - end-to-end acid injection with the reference and with a biased surrogate;
  - SGSIM I/O;
  - the Palandri & Kharaka (2004) parameter loader (`data/palandri_kharaka_2004_mt_simon.csv`, values read from the original report with table and page numbers).
- `examples/benchmark_full_grid.py` runs at production size (15×50×50, 1078 streamlines × 200 CVs, 215,600 CVs) with synthetic streamlines and calcite + dolomite:
  - operator build takes 0.2 s;
  - one reactive step takes about 12 s on one CPU core, almost all of it in the reference bisection;
  - relative mass-balance error is 10⁻¹⁴–10⁻¹⁵ per component;
  - per-mineral routing works as intended: after two steps, 259 calcite cells vs 10,239 dolomite cells are KINETIC.

  The 12 s step time is the cost a trained surrogate should remove.

## 7. Modelling assumptions for the depleted oil field (v0.1)

- **Residual oil** is immobile and non-reacting. It enters only through S_b = 1 − S_g − S_or, which the caller supplies. PAD-Stream has no oil phase; adding one is a separate milestone.
- **Asphaltene deposition** can be represented as an extra solid phase in `mineral_vf`. Its volume reduces porosity like a mineral. Its deposition kinetics are not implemented and need an oil-phase carrier.
- **CO2 dissolution** into brine is not implemented. It needs a solubility backend (Duan & Sun 2003 or Spycher et al. 2003) that adds dissolved inorganic carbon from the gas saturation. This is the first item to add after a speciation backend.
- **Reference chemistry** uses ideal activities with component totals as free activities. For production, implement `ChemistryBackend` on Reaktoro or PHREEQC, with Debye–Hückel/Pitzer activities, speciation and pH.
- **Temperature** is isothermal. The `temperature` field and the Arrhenius terms are already in place for a later thermal model.

## 8. Experiments that test the claims

1. **Claim 1, routing ablation.** Compare routing against all-equilibrium and all-kinetic runs, and against an a posteriori residual switch (Coatléven-style) using the same reference chemistry. Report chemistry calls, wall time and error relative to the all-kinetic run.
2. **Claim 2, surrogate inside streamlines.** Plot fallback rate against training-set size and against time, and show the cumulative mass error staying at round-off. Guérillot & Bruyelle 2020 report this error growing linearly.
3. **Claim 4, learned φ→k.** Compare the learned closure with Kozeny–Carman and Verma–Pruess (φ_c, n) against pore-scale or core data. Report how often the guard falls back.
4. **Retrace sensitivity.** Vary the |Δk/k| threshold (1–5 %) and compare against retracing every step.

## 9. 3D build housekeeping done on this branch

- `pyproject.toml` makes `padstream_rt` an installable package, with `pip install -e .[test]`.
- CI in `.github/workflows/tests.yml` runs pytest on Python 3.10 and 3.12.
- `requirements.txt` adds `scipy` and `highspy==1.15.1`, which the existing scripts import.
- `padstream_rt/io.py` reads the SG1 permeability file and the SG6 database without importing milestone scripts.

**Not changed. These are flagged for you to decide, because they alter certified milestone semantics:**

- Viscosities are 0.5 / 5 cP in V15–V16 but 0.05 / 0.60 cP in the v14 `CCUSFluid`.
- The CO2 "w/displacing" phase label in SG7A should be renamed to gas/brine before aqueous species are added.
- v14 has duplicate function definitions: `ccus_relative_permeability`, `trace_streamline` and `trace_streamline_detailed`.
- TensorFlow and PyTorch are both used. The recommendation is PyTorch for the chemistry surrogate.
