# Routing ablation and surrogate test: lower Mt. Simon layer (27 Oct 2026)

Script: `examples/routing_ablation.py`. Network: `examples/models/lower_mt_simon_speciation_v1.npz`
(trained by `examples/train_speciation_surrogate.py`).

## Set-up

- **Grid:** one 25 x 25 x 1 layer of PAD-Stream cells (20 x 20 x 4 ft).
- **Streamlines:** 200 synthetic quarter-five-spot streamlines, with the same flux per unit area as the 50 x 50 layer.
  - Residence time per cell: 8–151 days.
  - 114 of the 625 cells (18%) have no streamline.
- **Run length:** 12 steps of 30 days.
- **Rock:** lower Mt. Simon mineralogy from Freiburg et al. (2022), Table 1:
  - quartz, K-feldspar, plagioclase (as albite), siderite and illite;
  - kaolinite seeded at a volume fraction of 1e-4;
  - pyrite left out (its rate law needs O2/Fe3+);
  - geometric surface areas, roughness 1.
- **Kinetics:** Palandri & Kharaka (2004) parameters. Siderite and illite use the provisional values from Sun et al. (2020).
- **Conditions:** 50 °C and 150 bar.
- **Formation brine:** 2 m NaCl, equilibrated with quartz, kaolinite and K-feldspar at pCO2 = 0.1 atm.
- **Injected brine:** 2 m NaCl, CO2-saturated at 80 atm (pH about 3.0).
- **Brine saturation:** 0.6.
- **Truth:** PHREEQC `KINETICS` with the same rate laws, solved by CVODE in every (cell, mineral) pair.

Errors in the results table are relative L1 norms over all cells, measured against the truth run. They cover three quantities:

- the change in mineral volume (all minerals);
- the change in porosity;
- dissolved carbon.

Over the year, the truth run changes porosity by at most 1.1e-4. This agrees with Sun et al. (2020), who report porosity changes below 1% over 1000 years.

## Results

| Configuration | PHREEQC cell-solves | Wall time (s) | Mineral-volume error | Porosity error | Dissolved-C error |
|---|---|---|---|---|---|
| truth: PHREEQC kinetics everywhere | 7500 | 182 | — | — | — |
| all-equilibrium (common shortcut) | 7500 (equilibrium) | 11 | 606x | 197x | 3.3e-3 |
| Damköhler routing, c_eq scale | 7500 | 185 | 0 (all routed KINETIC) | 0 | 0 |
| saturation-aware Damköhler, stiff → EQUILIBRIUM | 7500 | 192 | 8.2x | 3.6x | 2.3e-5 |
| surrogate + a posteriori checks only | 2247 (30%) | 88 | 13.0% | 4.7% | 1.2e-6 |
| surrogate + a priori stiffness routing, S > 64 | 4369 (58%) | 132 | 4.0% | 2.2% | 1.1e-6 |
| surrogate + a priori stiffness routing, S > 8 | 4625 (62%) | 136 | 1.2% | 1.3% | 3.5e-7 |
| surrogate + a priori stiffness routing, S > 1 | 5805 (77%) | 161 | 0.08% | 0.30% | 1.0e-7 |

The mass-balance error stayed at or below 1.9e-14 in every run, which confirms that conservation holds by construction.

## Findings

### 1. The all-equilibrium shortcut is unusable for this rock

Its mineral changes are about 600 times too large: it dissolves feldspar and precipitates kaolinite and quartz to equilibrium in every cell.

### 2. Routing with the c_eq-based Damköhler number is correct here, but saves nothing

For a 30-day step in lower Mt. Simon silicates, Da_dt ranges from 6e-3 (kaolinite) to 0.92 (quartz), and Da_tau peaks at 4.6 (quartz). Every pair therefore falls between the skip threshold (1e-3) and the equilibrium threshold (10), so everything routes KINETIC and the result equals the truth. The EQUILIBRIUM and SKIP branches would only be used in these cases:

- carbonate cements;
- much longer steps;
- much smaller surface areas (roughness below 1).

The thesis should say this plainly.

### 3. Sending stiff, supersaturated pairs to EQUILIBRIUM is wrong

The saturation-aware Da (`damkohler.characteristic_concentration`) routes supersaturated feldspar to EQUILIBRIUM. Feldspar then precipitates all the way to equilibrium, which kinetics never allow at 50 °C, and the error grows 8x. Stiffness is a reason to change the integration method, not the physics.

### 4. Speciation is learned well; the remaining error comes from explicit integration

The network predicts pH with a mean absolute error of 0.005 (99th percentile 0.03) and saturation indices with errors of 0.009–0.016. To isolate the integrator, I replaced the network with exact PHREEQC speciation in the same 8-substep explicit integrator. That gives the same 13% error.

The cells where it fails are formation-brine cells close to equilibrium with feldspar, kaolinite and quartz. There the coupling through dissolved Al (about 1e-7 mol/kg) is stiff.

### 5. A priori stiffness routing is the decision that pays off here

`SpeciationSurrogate.stiffness` uses only the learned speciation, before any chemistry is solved. It computes S as the explicit step size divided by the moles still needed to reach equilibrium, and sends cells with S > S_max to the implicit PHREEQC reference.

At S > 8, the error falls about 11x (13% → 1.2%) compared with the surrogate checked only after the fact.

- **The cost:** about twice as many reference solves.
- **The saving:** wall time is 25% lower than the truth run, at 1.2% error.

### 6. Implications for the gap claims

- **Claim 1** is supported only in a revised form. The a priori router should choose among four chemistry treatments:
  - explicit surrogate;
  - implicit reference;
  - equilibrium;
  - skip.

  Damköhler numbers decide equilibrium and skip; the stiffness ratio decides surrogate versus implicit reference. As far as the literature search found, no published scheme routes on stiffness. Re-check this against Leal 2020 and Coatléven 2026 before putting it in the thesis.
- **Claim 2:** the surrogate with fallback works and conserves mass exactly. In this system, its speed is limited by how many cells are stiff, not by network accuracy.

## Limitations

- **Small domain:** one layer, a 25 x 25 grid and synthetic streamlines.
- **Assumed rock and fluid properties:** geometric surface areas, NaCl-only brine (IBDP brine is Na-Ca-Cl) and an assumed kaolinite seed.
- **Siderite and illite rate constants** are provisional (from Sun et al. 2020).
- **Damköhler thresholds not tested:** da_skip = 1e-2 and 1e-1 still need to be run.
- **Timing hardware:** 2 CPU cores.
- **Timings include transport.** PHREEQC KINETICS costs about 24 ms per cell; the surrogate itself costs under 0.1 ms per cell.
