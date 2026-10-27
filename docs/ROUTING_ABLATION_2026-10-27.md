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

  Damköhler numbers decide equilibrium and skip; the stiffness ratio decides surrogate versus implicit reference. Per-cell a priori solver selection already exists in combustion (Lapointe et al. 2020, doi:10.1016/j.combustflame.2020.06.033), so the claim is its transfer to mineral reactive transport with physical criteria. The Scopus check is in living-doc section 12.12; Web of Science is still to do.
- **Claim 2:** the surrogate with fallback works and conserves mass exactly. In this system, its speed is limited by how many cells are stiff, not by network accuracy.

## Limitations

- **Small domain:** one layer, a 25 x 25 grid and synthetic streamlines.
- **Assumed rock and fluid properties:** geometric surface areas, NaCl-only brine (IBDP brine is Na-Ca-Cl) and an assumed kaolinite seed.
- **Siderite and illite rate constants** are provisional (from Sun et al. 2020).
- **Skip threshold:** at da_skip = 1e-2 the router skips kaolinite everywhere (its Da_dt is 6e-3). No cell is skipped whole, so nothing is saved, and removing the Al sink made the PHREEQC reference 3–8x slower per step (more than 7 minutes at step 5 on a 10 x 10 layer, when the run was stopped). Skipping a secondary sink phase is harmful; the error was not measured.
- **Timing hardware:** 2 CPU cores.
- **Timings include transport.** PHREEQC KINETICS costs about 24 ms per cell; the surrogate itself costs under 0.1 ms per cell.


# Carbonate-bearing unit: Argenta (27 Oct 2026, later the same day)

Run with `--system argenta`. Network: `examples/models/argenta_speciation_v1.npz`, with pH MAE 0.005 and SI MAE 0.007–0.053 (chlorite is the worst).

## Set-up changes from the lower Mt. Simon runs

- **Mineralogy:** Freiburg et al. (2022), Table 1, Argenta row: quartz, K-feldspar, calcite, dolomite, illite, kaolinite and chlorite. Pyrite and hematite are inert.
- **Grain size:** "very fine to very coarse", assumed. The paper's own description runs from very fine sand to pebble.
- **Dolomite:** PK 2004 "disordered" parameters.
- **No kinetic precipitation of K-feldspar, illite or chlorite** (assumed). With the symmetric PK law, illite precipitation on 1-µm clay areas in fully acidified brine stalled PHREEQC KINETICS for more than 4 minutes per cell.
- **Formation brine:** equilibrated with quartz, kaolinite, K-feldspar, calcite and dolomite at pCO2 = 0.1 atm.

## 1. Damköhler routing now does work

At 30-day steps it routes every calcite and dolomite pair to EQUILIBRIUM, where Da_dt runs from 2e2 to 1e5. Kaolinite also goes to EQUILIBRIUM at the inlet (Da_dt 16), and the silicates stay KINETIC.

## 2. Full kinetics is impractical

One cell and one 30-day step, single-cell test (`local_arg.py` in the scratch folder). The routed result uses the new kinetic-then-equilibrium order with 6 substeps.

| Inlet-brine fraction | PHREEQC full kinetics (s) | Routed (s) | Routed error | All-equilibrium error |
|---|---|---|---|---|
| 0 (formation brine) | 2.5 | 2.2 | 76% (small absolute change) | 2951x |
| 0.25 | 11.6 | 2.4 | 16% | 92x |
| 0.50 | 52.4 | 1.8 | 0.12% | 90x |
| 0.75 | 84.7 | 1.9 | 0.53% | 89x |
| 1.0 | 165.7 | 1.9 | 22% (kaolinite also at equilibrium) | 89x |

## 3. The order of the split matters

The v0.3.0 coupling did equilibrium first, then kinetics. That misses Mg released by chlorite, which full kinetics precipitates as dolomite. Errors per order, in the same single-cell test:

| Inlet-brine fraction | Equilibrium → kinetic | Kinetic → equilibrium | Kinetic → equilibrium, 6 substeps |
|---|---|---|---|
| 0.25 | 86% | 58% | 16% |
| 0.50 | 74% | 20% | 0.12% |
| 0.75 | 64% | 1.2% | 0.53% |

`reactive_step` now defaults to `chem_order=("kinetic", "equilibrium")` and takes `chem_substeps`.

## 4. Coupled run

6 x 6 layer, 4 steps of 30 days, 6 chemistry substeps. The reference is the Damköhler-routed PHREEQC run, because full kinetics is too slow.

| Configuration | Time (s) | Mineral-volume error | Porosity error | Dissolved-C error |
|---|---|---|---|---|
| Damköhler-routed PHREEQC (reference) | 135 | — | — | — |
| All-equilibrium | 1.6 | 46x | 41x | 93% |
| v0.3.0 split (equilibrium first, 1 substep) | 71 | 51% | 178% | 66% |
| Four-way router (surrogate + stiffness S > 8) | 170 | 3e-5 | 4e-4 | 1e-5 |

Mass balance held to 7.6e-16 in every run except all-equilibrium (7.3e-13).

## 5. The surrogate barely runs here

90% of the kinetic cell-solves were stiff and went to PHREEQC a priori, and 12 more were rejected. The surrogate handled only 72 of 864 (8%). The four-way router is therefore accurate but slower than the reference: its checks add overhead and almost nothing goes to the surrogate.

Brine buffered by calcite and dolomite sits near equilibrium with the silicates, which is the stiff regime found in the lower Mt. Simon formation brine. In this unit, the gain comes from Damköhler routing of the carbonates (full kinetics is 1–90x slower per cell), not from the surrogate.

## 6. Reporting note

`SurrogateBackend` now counts equilibrium calls that the speciation surrogate declines as routed to the reference, not as model errors. The coupled run above used the old counting: 864 "model_error" are those equilibrium calls.
