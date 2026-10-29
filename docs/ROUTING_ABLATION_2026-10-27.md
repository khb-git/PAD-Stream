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

## 7. Sensitivity: silicate precipitation and clay surface area

Argenta, 6 x 6 layer, 4 steps of 30 days, routed PHREEQC reference, 6 substeps.

- `--allow_precipitation` turns the symmetric PK law back on for K-feldspar, illite and chlorite.
- `--clay_roughness` scales the geometric area of illite, kaolinite and chlorite only.
- Changes are summed over the layer. Carbonate C = Δcalcite + 2 Δdolomite (mol).

| Clay area factor | Silicate precipitation | Time (s) | Mean Δφ | Max abs Δφ | Dissolved C (mol) | Δ carbonate C (mol) | Δ dolomite (mol) | Δ chlorite (mol) |
|---|---|---|---|---|---|---|---|---|
| 1 (geometric) | off (baseline) | 135 | -1.49e-4 | 4.30e-4 | 23,940 | +30,840 | +32,524 | -6,689 |
| 1 | on | > 500 for step 1 (stopped) | — | — | — | — | — | — |
| 0.1 | off | 47 | +6.15e-5 | 4.02e-4 | 50,569 | +631 | +3,439 | -1,011 |
| 0.1 | on | 48 | +6.10e-5 | 4.02e-4 | 50,567 | +645 | +3,457 | -1,015 |
| 0.01 | off | 27 | +9.28e-5 | 4.43e-4 | 54,550 | -4,028 | -1,083 | -125 |
| 0.01 | on | 23 | +9.25e-5 | 4.43e-4 | 54,548 | -4,017 | -1,071 | -128 |

**Findings**

- **The precipitation assumption is immaterial wherever the model can run.** At the same clay area, allowing K-feldspar, illite and chlorite to precipitate changes:
  - mean Δφ by 0.3–0.9%;
  - dissolved C by less than 1e-4 (relative);
  - carbonate C by at most 2.2%.

  Illite still dissolves overall when allowed to precipitate. K-feldspar switches from -19 to +21 mol, which is negligible.
- **At full geometric clay area, allowing precipitation makes the reference intractable.** Step 1 did not finish in 500 s; the baseline took 27 s.
- **Clay reactive surface area is the first-order uncertainty.** Cutting it 10x changes carbonate trapping 49x (+30,840 → +631 mol), doubles dissolved C, and flips the sign of the mean porosity change. The mechanism is chlorite dissolution, which supplies Mg that precipitates as dolomite.
- **What this means:** the dissertation should state dissolution-only primary silicates as an assumption, backed by this table and the Freiburg et al. (2022) illite K-Ar ages. It should treat clay reactive surface area as a parameter to constrain, through BET data or a range, and to propagate as uncertainty.

## 8. Clay reactive surface area: literature range and uncertainty band

Same Argenta set-up as section 7, dissolution-only silicates, `--clay_roughness` 1 / 0.1 / 0.01 / 0.001. That is
about 2.2e4 / 2.2e3 / 2.2e2 / 22 cm2/g, from 6/(rho d) with d = 1 um.

| Clay area (cm2/g) | Mean Δφ | Dissolved C (mol) | Δ carbonate C (mol) | Δ dolomite (mol) | Δ chlorite (mol) |
|---|---|---|---|---|---|
| 2.2e4 | -1.49e-4 | 23,940 | +30,843 | +32,524 | -6,689 |
| 2.2e3 | +6.15e-5 | 50,569 | +631 | +3,439 | -1,011 |
| 2.2e2 | +9.28e-5 | 54,550 | -4,028 | -1,083 | -125 |
| 22 | +9.68e-5 | 54,989 | -4,617 | -1,652 | -14 |

**Literature range** (DOIs checked):

- **Black, Carroll & Haese (2015, doi:10.1016/j.chemgeo.2014.09.020, Fig. 4).** Clay areas used in models fall at
  about 10 to 3e4 cm2/g. BET-measured values are higher: chlorite about 2e4–7e4, kaolinite about 5e4–1.2e5,
  illite–smectite about 3e5–1e6 cm2/g. These were read from a log-scale figure and are approximate.
- **Xu, Apps & Pruess (2005, doi:10.1016/j.chemgeo.2004.12.015, Table 1).** Clays 151.6 cm2/g and chlorite
  9.8 cm2/g, both reduced 10x in their runs.
- **Beckingham et al. (2017, doi:10.1016/j.gca.2017.02.006).** Field-accessible areas needed a 10–20x reduction to
  match their core flood.

**Recommendation:** use a clay factor of 0.01 (about 2e2 cm2/g) as the central value, and report 0.1 and 0.001 as
bounds. Below about 2e2 cm2/g the results converge.

**Brine:** `data/liu2011_mt_simon_brine.csv` holds a Mt. Simon Na–Ca–Cl brine from Liu et al. (2011, Table 3,
after Eliasson et al. 1998). It is Indiana well data, not IBDP. It is not yet used by the examples.

## 9. Mt. Simon brine (Liu et al. 2011) instead of 2 m NaCl

Defaults now are: clay area factor 0.01, and a Na–Ca–Mg–Cl–SO4 brine for the new systems `lower_mt_simon_brine`
and `argenta_brine`.

**Brine handling:**

- The brine is Table 3 of Liu et al. (2011), doi:10.1016/j.ijggc.2010.08.008, after Eliasson et al. (1998),
  Indiana well data.
- The measured pH of 6.9 is kept. Charge is closed on Cl, because the analysis has about a 1% anion excess, and
  balancing that on pH gave pH 3.3.
- Only quartz and kaolinite are equilibrated, plus calcite and dolomite in the Argenta. Forcing K-feldspar
  equilibrium at 50 C dissolved about 0.1 mol/kg of feldspar, which contradicts the measured K.
- The injected brine is the same brine, CO2-saturated at 80 atm.
- Calcite and anhydrite are possible secondary phases, seeded at a volume fraction of 1e-6.

**Reference:** routed PHREEQC (`da_ref`). Full kinetics stalled, because calcite is kinetic in the "truth" run.
Primary silicates are dissolution-only throughout.

| Case | Grid, time | Mean Δφ | Max abs Δφ | Dissolved C (mol) | Δ carbonate C (mol) | Main mineral changes (mol) |
|---|---|---|---|---|---|---|
| Lower Mt. Simon, NaCl | 10x10, 12 x 30 d | +1.67e-5 | 8.8e-5 | 318,763 | -483 | quartz +3,190; K-feldspar -729; albite -538; siderite -483 |
| Lower Mt. Simon, brine | 10x10, 12 x 30 d | +2.29e-5 | 8.6e-5 | 269,752 | -757 | quartz +4,498; K-feldspar -792; albite -919; siderite -743; no calcite growth |
| Argenta, NaCl | 6x6, 4 x 30 d | +9.28e-5 | 4.4e-4 | 54,550 | -4,028 | calcite -1,862; dolomite -1,083; chlorite -125 |
| Argenta, brine | 6x6, 4 x 30 d | +3.09e-5 | 1.3e-4 | 44,136 | -1,950 | calcite +5,854; dolomite -3,902; chlorite -115 |

**Findings**

- **Less carbon dissolves in the real brine:** 15% less in the lower Mt. Simon and 19% less in the Argenta. CO2
  solubility is lower in the Ca–Mg-rich, higher-ionic-strength brine. Note that phreeqc.dat is used here at
  I ≈ 3 mol/kg, outside its comfort range.
- **In the Argenta the brine flips calcite from dissolving to precipitating** (+5,854 mol), while dolomite
  dissolves. Net carbonate C still falls, but by half as much as with NaCl, and the porosity change is about 3x
  smaller.
- **No carbonate trapping appears in the lower Mt. Simon within a year**, and silicate dissolution rises 9–71% (K-feldspar +9%, albite +71%).
- **The Damköhler router now uses all three routes.** In the lower Mt. Simon brine run, calcite is SKIP in 88 cells
  and EQUILIBRIUM in 12; anhydrite is SKIP; kaolinite is SKIP.
- **Seeds matter.** With 1e-4 seeds, the seeds themselves dissolved (calcite -8,034 and anhydrite -5,368 mol) and
  inflated the mean porosity change about 6x. The brine systems therefore default to 1e-6 seeds. In the Argenta,
  the carbonate result is unchanged by the seed size (-1,954 vs -1,950 mol).
- **The speciation networks were trained on NaCl brines.** The surrogate configurations need retraining before they
  are used with the brine systems.

## 10. Pilot: learn the PHREEQC step itself (`StepSurrogate`, config `da_step`)

**Setup.** The network predicts the mineral extents of one PHREEQC KINETICS (CVODE) step from:

- the element molalities, charge feature, T, P and dt;
- the reactive area and amount of the 5 kinetic minerals (quartz, K-feldspar, albite, siderite, illite);
- pH and the saturation indices of those minerals, both from exact PHREEQC speciation (about 0.15 ms per cell).

**Safeguards.**

- The exact positivity limiter is applied to every prediction.
- Cells outside the training feature box, or asking for other kinetic minerals, go straight to PHREEQC.
- If a predicted step carries a saturation index across equilibrium by more than 0.05, that mineral's extent is
  halved, up to 4 times, using exact speciation.
- SurrogateBackend's checks then send any remaining failures to PHREEQC.

**Training data** (`examples/generate_step_data.py`, `examples/train_step_surrogate.py`):

- 35,200 samples, 27 ms each, generated in roughly 8-minute chunks.
- Sampled states: mixtures of formation and injected Liu brine, with the conservative ions varied ±25% and carbon
  varied 30x.
- Held-out relative error: 2.7–4.4% per mineral.
- The first data set held the brine ions fixed. On that set every coupled cell left the training box after one
  step, which is why the second, varied set was needed.

**Test.** Lower Mt. Simon with the Liu brine, 10 x 10 layer, 12 x 30 d. The reference is Damköhler-routed PHREEQC.
The coupled states were not used for training.

| Configuration | Time (s) | PHREEQC cell-solves | Kinetic cells on the surrogate | Mineral-volume error | Porosity error | Dissolved-C error |
|---|---|---|---|---|---|---|
| Routed PHREEQC (reference) | 29.5 | 1200 | — | — | — | — |
| Step surrogate, SI inputs + overshoot repair | 15.2 | 731 | 903 / 1200 (75%) | 3.8% | 2.0% | 2.4e-5 |
| Step surrogate, SI inputs, no repair | 15.4 | 793 | 841 / 1200 (70%) | 3.7% | 2.1% | 2.3e-5 |
| First attempt: fixed-ion data, composition inputs only (no SI) | 28.3 | 1600 | 34 / 1200 (3%) | 1.3%* | 2.4% | 5e-6 |

*Low only because almost every cell fell back to PHREEQC.

**Pilot criteria were 70% of cells accepted and under 5% error. Both are met** (75% and 3.8%), with a 1.9x speed-up
in wall time. Mass balance held to 3e-15.

What limits the speed-up now is not PHREEQC KINETICS but:

- the speciation calls (3–6 per cell, for features, repair and checks);
- the equilibrium cells (calcite, about 36 per step).

Where the remaining rejections come from: of the 1200 kinetic cells, 37 left the training box and 260 were
rejected for overshoot.

**What this means for claim 2.** A learned PHREEQC step, with exact speciation as its input and its check, works
where the explicit-kinetics surrogate failed (13% error, or 62% of cells sent to PHREEQC).

The ML part is the time integration of stiff kinetics. That is the expensive and stiff part, and the part
Section 4 showed explicit methods cannot do.

**Not yet tested:**

- the Argenta brine case (carbonate-buffered, the stiffest);
- longer runs;
- 3D;
- a speciation network in place of PHREEQC speciation, which would cut the remaining cost.

## 11. Step surrogate on the Argenta brine case (the stiffest)

**Setup.**

- Kinetic minerals: quartz, K-feldspar, illite, kaolinite and chlorite. Calcite, dolomite and anhydrite are
  solved at equilibrium.
- Training data: 23,800 PHREEQC KINETICS samples at about 112 ms each, 4x the lower Mt. Simon cost.
- dt ranges over 1–60 d, and half the samples were first equilibrated with the carbonates.
- Held-out relative L1 error: 4.4–8.8% per mineral. A larger network trained for longer did no better.

**Test.** 6 x 6 layer, 4 x 30 d, 6 chemistry substeps. The reference is Damköhler-routed PHREEQC.

| Configuration | Time (s) | Kinetic cell-solves on the surrogate | Volume error, all minerals | Volume error, kinetic minerals only | Dissolved-C error |
|---|---|---|---|---|---|
| Routed PHREEQC (reference) | 42.0 | — | — | — | — |
| Step surrogate (`da_step`) | 24.5 | 534 / 864 (62%) | 0.37% | 3.1% | 1.2e-4 |

Per-mineral errors: quartz 6.2%, K-feldspar 9.3%, illite 15% (small absolute change), kaolinite 2.7%,
chlorite 0.9%.

The all-minerals volume error is flattering, because the carbonates dominate the volume change and are solved
exactly at equilibrium. The kinetic-only figure (3.1%) is the honest one.

**Against the pilot criteria:**

- The error criterion is met: 3.1% kinetic-only, against a target under 5%.
- The acceptance criterion is missed: 62%, against a target of at least 70%. Of the 330 kinetic cell-solves sent
  to PHREEQC, 311 failed the overshoot check after repair and 19 fell outside the training box.
- The run was still 1.7x faster.

**What this means for claim 2.** The step surrogate holds its accuracy in both units. In carbonate-buffered rock
it covers about 60% rather than 75% of cells. The remaining overshoot rejections are cells near
silicate–carbonate equilibrium.

Options:

- **More data near equilibrium:** focused samples of carbonate-equilibrated states.
- **A softer overshoot test:** accept crossings within the network's own error band.
- **State it as is:** acceptance depends on how close the rock sits to equilibrium.

## 12. Argenta: focused near-equilibrium training data (step surrogate v2)

**Method (offline active learning).**

1. Harvest: `examples/harvest_step_states.py` runs `da_step` with the v1 network on two coupled cases that are
   not the test case: 5 x 5, 5 x 20 d, and 4 x 4, 4 x 45 d (test: 6 x 6, 4 x 30 d). It saves every kinetic
   cell the surrogate could not take: 365 states, almost all overshoot rejections. In these states quartz
   (median SI +0.2 to +0.5) and kaolinite (median SI +0.1 to +1.2) sit near saturation, where a small extent
   error flips the sign of SI.
2. Label: `examples/generate_step_data_focused.py` perturbs each state 36 times and runs PHREEQC KINETICS.
   - Al and Si are varied ±0.4 log units, so the samples straddle quartz and kaolinite saturation.
   - K and C are varied ±0.2 log units, and the other ions ±0.05.
   - Mineral amounts vary ±20%, area ±0.3 log units, and dt over 1–15 d.
   - This gives 13,140 samples at about 55 ms each (12 min on 2 cores).
3. Retrain on the 23,800 broad and 13,140 focused samples (same network size, 300 epochs, 157 s), giving
   `examples/models/argenta_brine_step_v2.npz`.

No state from either test case was used in training. This is the offline counterpart of the on-demand
retraining of Leal et al. (2020).

**Held-out error (relative L1 per mineral).**

| Held-out set | Quartz | K-feldspar | Illite | Kaolinite | Chlorite |
|---|---|---|---|---|---|
| Broad samples | 18% | 8.1% | 6.1% | 12% | 8.1% |
| Focused samples | 38% | 5.6% | 3.4% | 10% | 5.3% |

On the broad set this is worse than v1 (4.4–8.8%). Quartz extents in the focused samples are tiny, so their
relative error is large.

**Coupled tests.** The reference is Damköhler-routed PHREEQC. Case A is the Section 11 test. Case B is a second
unseen case: 7 x 7, 4 x 25 d.

(The permeability seed in `build` turned out not to change the run, because the synthetic streamlines do not use
the permeability field. A seed-7 copy of case A reproduced it exactly, so case B differs in grid and time step
instead.)

| Case | Network | Time (s) | Kinetic cells on the surrogate | Overshoot rejections | Volume error, kinetic minerals | Dissolved-C error |
|---|---|---|---|---|---|---|
| A: 6x6, 4 x 30 d (ref. 42.0 s) | v1 | 24.5 | 534 / 864 (61.8%) | 327 | 3.1% | 1.2e-4 |
| A | v2 | 25.7 | 618 / 864 (71.5%) | 246 | 4.3% | 5.9e-4 |
| B: 7x7, 4 x 25 d (ref. 79.4 s) | v1 | 42.1 | 793 / 1176 (67.4%) | 378 | 4.8% | 1.3e-4 |
| B | v2 | 40.1 | 763 / 1176 (64.9%) | 413 | 3.7% | 3.9e-4 |

Per-mineral errors, case B:

- v1: quartz 10%, K-feldspar 15%, illite 21%, kaolinite 4.2%, chlorite 1.1%.
- v2: quartz 4.6%, K-feldspar 7.0%, illite 7.3%, kaolinite 2.6%, chlorite 3.3%.

Mass balance held to 4e-15 throughout.

**Result: the focused data did not raise acceptance reliably.**

- In case A it lifted acceptance past the 70% target (61.8% to 71.5%), but the error rose (3.1% to 4.3%).
- In case B acceptance fell (67.4% to 64.9%), while the error improved (4.8% to 3.7%).
- With either network, acceptance across the two cases spans 62–72%, and the speed-up over routed PHREEQC is
  1.7–2.0x.

**Reading.**

- More data near equilibrium mainly moves error around: per-mineral errors became more even, especially in
  case B.
- It does not lift the acceptance ceiling. The binding constraint seems to be the overshoot test itself: a
  0.05 tolerance on an SI sign flip, for minerals sitting at SI ≈ 0 with Al and Si near 1e-7 mol/kg. Any
  prediction error of a few percent crosses it.
- That makes option 2 (a tolerance matched to the network's error) a question about the check, not the data.
  Whether a crossing of a given size matters can be tested directly: accept it, then compare against the
  reference.

**For claim 2, as it stands:**

- The learned step holds under 5% kinetic-mineral error in all four Argenta runs and in the lower Mt. Simon.
- It takes 62–72% of kinetic cells in the carbonate-buffered Argenta and 75% in the lower Mt. Simon.
- It runs at 1.6–2.0x the speed of routed PHREEQC.
- v1 stays the default; v2 is kept for the comparison.

**Counting.** `FallbackStats` now records cells offered and accepted per mode (`offered`, `accepted`,
`acceptance()`), and the ablation prints "kinetic cells on the surrogate" directly. It reproduces the hand
counts in Sections 10 and 11 (903 / 1200 and 534 / 864).


## 13. The overshoot check: test it directly (option 2)

Section 12 left the overshoot check as the suspected ceiling on acceptance. The check rejects a cell when a
mineral's saturation index changes sign by more than 0.05 over the step, and the repair first halves such
extents up to 4 times.

**New code.**

- `SurrogateBackend(omega_tol=...)` takes one tolerance per mineral (`np.inf` switches the check off).
- `routing_ablation.py --omega_tol {number | inf | cal}`, where `cal` reads `<step_net>_tol.json`.
- `examples/overshoot_tolerance_calibration.py`: tolerance from held-out data.
- `examples/overshoot_tolerance_sweep.py`: coupled sweep. It also counts how often the reference's own kinetic
  solves would fail the check.

### 13.1 Does PHREEQC itself pass the check?

The routed-PHREEQC reference was run with every kinetic solve also put through the sign-flip check.

| Run | Kinetic solves | Fail at 0.05 | 0.2 | 0.5 | 1.0 |
|---|---|---|---|---|---|
| Argenta A (6x6, 4 x 30 d) | 864 | 36% | 33% | 11% | 7% |
| Argenta B (7x7, 4 x 25 d) | 1176 | 43% | 28% | 8% | 5% |
| Argenta A, 12 x 30 d | 2592 | 17% | 16% | 9% | 5% |
| Lower Mt. Simon (10x10, 12 x 30 d) | 1200 | 38% | 19% | 14% | 14% |

On held-out training samples the figures are 34–44% at 0.05.

**So the check rejects the reference in up to 43% of solves.** In a multi-mineral system, a mineral's SI often
changes sign during a step for real reasons: another mineral's reaction carries it across saturation (feldspar
dissolution supplying Al and Si, which saturates kaolinite and quartz). The check was written for single-mineral
overshoot, and in these systems it mostly flags physics.

A narrower **direction check** was also tried: flag only when a mineral's own extent carries it past
equilibrium (it dissolved yet ends supersaturated). PHREEQC fails it rarely in the Argenta (1–4.5%), but in
20% of lower Mt. Simon samples at 0.05. The network fails it in 22–44%. It was not taken further.

### 13.2 Network error expressed as SI

For each held-out sample, SI at the end of the step was computed from the predicted and from the PHREEQC extents.
The table gives the 95th percentile of the difference, in log units (v1 networks). These values are the
error-matched tolerances, stored as `<net>_tol.json`.

| Mineral | Argenta | Lower Mt. Simon |
|---|---|---|
| Quartz | 0.21 | 0.13 |
| K-feldspar | 2.7 | 0.43 |
| Albite | — | 0.48 |
| Siderite | — | 0.06 |
| Illite | 6.5 | 0.42 |
| Kaolinite | 5.6 | — |
| Chlorite | 8.3 | — |

The network predicts the *extents* to 4–9%, but in the Argenta the end-of-step Al is a small difference between
feldspar and clay dissolution and kaolinite precipitation. Its SI is not resolved to better than several log
units. At the network's accuracy, an SI check means something only for quartz there, and for every mineral in
the lower Mt. Simon.

### 13.3 Coupled sweep

All runs use the v1 networks. The reference is routed PHREEQC, timed alone: A 42.0 s, B 79.4 s, A-12 131.6 s,
lower Mt. Simon 29.5 s. The surrogate runs shared 2 cores with another job, so their times are upper bounds.

Each cell gives the share of kinetic cells accepted / the volume error on the kinetic minerals.

| Tolerance | Argenta A | Argenta B | Lower Mt. Simon |
|---|---|---|---|
| 0.05 (default) | 61.8% / 3.1% | 67.4% / 4.8% | 75.2% / 3.7% |
| 0.2 | 64.0% / 3.8% | 71.0% / 5.3% | 77.9% / 3.8% |
| 0.5 | 70.1% / 4.6% | 79.8% / 6.2% | 83.0% / 4.0% |
| 1.0 | 76.3% / 4.1% | 85.1% / 6.7% | 82.2% / 4.0% |
| no check, no repair | 80.4% / 2.4% | 83.8% / 3.3% | 96.2% / 4.2% |
| **calibrated (`cal`)** | **95.9% / 3.5%** | **97.3% / 4.5%** | **81.5% / 4.0%** |

With `cal`, the Argenta runs take 6.2 s (A) and 7.0 s (B), 7–11x faster than routed PHREEQC.

**Longer run** (Argenta A, 12 x 30 d, v1). The error does not grow with time.

| Tolerance | Accepted | Kinetic-mineral error | Time (s) |
|---|---|---|---|
| 0.05 | 68.8% | 1.2% | 73.4 |
| no check | 88.2% | 1.6% | 35.4 |
| cal | 96.4% | 1.6% | 17.4 (7.6x) |

Mass balance held to 4e-15 in every run.

**Repair and check, separately** (Argenta A, v1). With repair off, the check sends many more cells to PHREEQC:
acceptance is 43% at 0.05, 46% at 0.5 and 58% at `cal`. The error falls to 0.7–0.9%, simply because more of
the cells are solved by PHREEQC. So the repair is what lets about 20 points of cells through.

**v2 network.** With `cal`, v2 reaches 96–97% in A and B, but its error in B is 5.3%, which misses the target.
v1 stays the network of record.

### 13.4 What this settles

- **The acceptance ceiling came from the check, not the network.** PHREEQC itself fails that check in up to 43%
  of coupled solves.
- **With a tolerance matched to the network's own held-out SI error, v1 meets both pilot criteria in every
  run.** In the Argenta that is 96–97% accepted and under 5% error at 7–11x the speed of routed PHREEQC,
  including the 12-step run. In the lower Mt. Simon it is 81.5% accepted at 4.0% error.
- **Without any check, the error stayed under 5% as well.** In these runs the error is bounded by the network's
  accuracy and by the training-box routing, not by the overshoot check.

**What protects the result once the check is relaxed:**

- conservation by extent and the exact positivity limiter (both unchanged);
- training-box routing (routes 16–20% of Argenta cells when the check is off);
- the quartz check (0.21) in the Argenta, and all the checks in the lower Mt. Simon.

**Caveat.** For the Argenta aluminosilicates, the calibrated tolerance (2.7–8.3) leaves no working SI safeguard.
It is matched to what the network can resolve, and the coupled error confirms that this is enough here. It is
not a guarantee for states far from training.

**For claim 2:** use v1 with the calibrated tolerance and state the guarantees as conservation, positivity and
range routing. Report the SI check as calibrated to the network's held-out error. Keep the 0.05 default in the
code for comparison.

**Still untested:** 3D, longer horizons than 1 yr, and a second rock system for the calibration procedure itself.

## 14. Ten-year runs (28 Oct 2026)

`examples/long_run.py` runs a configuration year by year (12 × 30 d) with a checkpoint after each year,
and `--compare` prints the error against the reference by year. Same layers as before (Argenta 6 × 6 with
6 chemistry substeps; lower Mt. Simon 10 × 10 with 1); v1 networks.

| Year | Argenta, `cal`: accepted / kinetic-vol err | Argenta, 0.05 | Lower Mt. Simon, `cal` | Lower Mt. Simon, 0.05 |
|---|---|---|---|---|
| 1 | 96.4% / 1.6% | 68.8% / 1.2% | 81.5% / 4.0% | 75.2% / 3.7% |
| 2 | 96.6% / 1.3% | 71.3% / 0.9% | 94.0% / 4.4% | 86.0% / 4.2% |
| 5 | 96.8% / 1.2% | 71.4% / 0.9% | 94.0% / 4.6% | 86.0% / 4.5% |
| 10 | 96.8% / 1.2% | 73.1% / 0.8% | 94.0% / 4.6% | 86.0% / 4.5% |

- **The error does not grow.** Relative to the cumulative change it falls slightly in the Argenta and levels
  off at about 4.6% in the lower Mt. Simon after year 3.
- **Porosity error** stays at 0.1–0.2% (Argenta) and 4.0% (lower Mt. Simon); dissolved-C error under 1e-4.
- **Speed (wall time per year, two jobs sharing 2 cores):** Argenta 53 s routed PHREEQC, 8.4 s with `cal`
  (6.3×), 28 s with 0.05 (1.9×); lower Mt. Simon 13 s, 4 s (3.1×), 5 s.
- Mass balance held to 1.5e-15 in every year.

The lower Mt. Simon's acceptance rises after year 1 because the early, far-from-equilibrium transient is when
cells leave the training box.

## 15. Second rock system: Upper Mt. Simon (28 Oct 2026)

**System** (`upper_mt_simon_brine`): Freiburg et al. (2022) Table 1, feldspar-rich: 33% quartz, 42% K-feldspar,
10% plagioclase, 10% clay (illite/mica, I/S and chlorite), 1% calcite, 2% siderite, 1% dolomite; porosity 9.3%.
Liu brine, 6 chemistry substeps. Kinetic: quartz, K-feldspar, albite, siderite, illite, chlorite, kaolinite;
calcite, dolomite and anhydrite at equilibrium. Freiburg et al. list this unit as a seal (0.74 mD) with no
grain-size description, so "fine" is assumed; it is run on the same synthetic streamlines as a chemistry test,
not as a flow scenario.

**Procedure, same as for the other units:**

1. 24,000 PHREEQC KINETICS samples (`examples/generate_step_data_system.py`, about 64 ms each, porosity sampled
   around the unit's own 9.3%) and a 3 × 160 network (`examples/train_step_surrogate_system.py`): held-out error
   5.1–9.7% per mineral (v1).
2. Calibration on the held-out split. PHREEQC itself fails the 0.05 sign-flip check in 47% of samples (34–41% of
   coupled solves). Network SI error, 95th percentile: quartz 0.53, siderite 1.3, K-feldspar 4.0, albite 3.8,
   chlorite 4.4, kaolinite 4.1, illite 7.2 log units.

**First result: v1 fails the error target.**

| Network | Check | Case A (6×6, 4 × 30 d) | Case B (7×7, 4 × 25 d) |
|---|---|---|---|
| v1 | 0.05 | 87.6% / 11.9% | 90.5% / 9.5% |
| v1 | `cal` | 94.0% / 21.5% | 94.6% / 15.5% |
| v1 | none | 99.0% / 29.8% | 98.8% / 21.1% |

(accepted kinetic cells / kinetic-mineral volume error). Almost every coupled state was inside the training box,
but the network was inaccurate there: quartz 28–44%, albite 10–207%, illite 20–39%.

**Fix: on-distribution training data.** `harvest_step_states.py --all_reference` records every kinetic PHREEQC
solve of two non-test routed runs (5 × 5, 5 × 20 d; 4 × 4, 4 × 45 d): 1,134 states, perturbed into 9,072 more
samples (`generate_step_data_focused.py --system`). Retrained on all 33,072 (v2).

| Network | Check | Case A | Case B |
|---|---|---|---|
| v2 | 0.05 | 84.0% / **3.3%** | 86.6% / **4.8%** |
| v2 | `cal` (95th pct) | 94.1% / 4.7% | 94.6% / 5.6% |
| v2 | 90th-percentile tolerance | 93.6% / 4.4% | 94.4% / 5.1% |
| v2 | none | 97.3% / 21.7% | 97.0% / 31.2% |

Routed PHREEQC takes 10.9 s (A) and 13.5 s (B); the surrogate runs take 4.5–7.2 s, so 1.5–2.7× faster. The
feldspar-rich rock is cheap for PHREEQC, so the gain is smaller than in the Argenta.

**What carries over and what does not:**

- **The calibration procedure carries over for acceptance:** 94–95% with `cal` in both cases, as in the Argenta.
- **The accuracy does not carry over automatically.** It depended on training data drawn from the coupled-state
  distribution (v1 → v2: error 12% → 3–5%). Box routing cannot catch this: the states were inside the box.
- **In this rock the overshoot check is doing real work.** With no check the error is 22–31% (K-feldspar
  100–135%), unlike the Argenta, where no check stayed under 5%.
- **Best setting here is the stricter one:** the 0.05 check passes both targets (84–87%, 3.3–4.8%); `cal` passes
  in case A and misses by 0.6 points in case B.

**For claim 2:** the defensible procedure is (1) broad samples, (2) on-distribution samples harvested from non-test
routed runs, (3) per-mineral tolerance from held-out SI error, checked against a coupled reference, with the
fixed 0.05 check as the fallback where the calibrated one misses.

## 16. Chemistry assumptions (28 Oct 2026)

Routed-PHREEQC runs (`examples/chem_sensitivity.py`; Argenta 6 × 6, 4 × 30 d; lower Mt. Simon 10 × 10, 12 × 30 d).

**Dissolution-only primary silicates.** Rerun with the symmetric PK law for every mineral (`--variant precip`):

| Case | Dissolved C | Carbonate-mineral C | max \|Δφ\| |
|---|---|---|---|
| Argenta, dissolution-only (default) | +43,994 mol | −1,950 mol | 1.32e-4 |
| Argenta, symmetric | +43,995 | −1,952 | 1.32e-4 |
| Lower Mt. Simon, dissolution-only | +268,822 | −757 | 8.62e-5 |
| Lower Mt. Simon, symmetric | +268,806 | −739 | 8.62e-5 |

A 10-year Argenta run with the symmetric law (`long_run.py --allow_precipitation`) matches the default to within
2 mol of 44,000 in carbonate C at years 1, 5 and 10. **The assumption is now harmless:** with the 0.01 clay-area
default the primary silicates stay undersaturated, so they never precipitate, and PHREEQC no longer stalls (it did
at geometric clay areas). It can be stated as a check rather than an assumption.

**Secondary-mineral seed volume fraction** (default 1e-6):

| Case | 1e-7 | 1e-6 (default) | 1e-5 |
|---|---|---|---|
| Argenta, carbonate-mineral C | −1,950 | −1,950 | −1,951 |
| Lower Mt. Simon, carbonate-mineral C | −671 | −757 | −1,726 |

The Argenta is insensitive. In the lower Mt. Simon, 1e-5 seeds of calcite and anhydrite dissolve in the acid
front (calcite −986, anhydrite −988 mol) and double the carbonate-C loss; between 1e-7 and 1e-6 the result moves
by 11%. Report 1e-6 with this band.

**Inert pyrite and hematite.** If all Fe in them became siderite, the carbon it could trap is 177 mol/m³ (lower
Mt. Simon, 1% pyrite), 499 mol/m³ (Argenta, 1% pyrite + 1% hematite) and 301 mol/m³ (Upper Mt. Simon, 1% hematite).
The 10-year carbonate-C change in the Argenta layer is −27 mol/m³. So these minerals could matter if they react,
but releasing their Fe needs a redox driver: a reductant for hematite (H2S, CH4 or residual hydrocarbons, which a
depleted reservoir has) or an oxidant for pyrite. With CO2 and brine alone they are stable. Keep them inert for
the aquifer cases and flag them for contribution 3. Field evidence: Frio brine Fe rose after CO2 breakthrough
(Kharaka et al. 2006); at IBDP, VW1 zone 5 Fe rose from 33–75 to 354 mg/L by Round 10 (Iranmanesh et al. 2024
data), although the report links that zone's changes to CO2 migration in the well annulus.

**Measured IBDP brine.** Iranmanesh et al. (2024, ISGS Circular 611, https://hdl.handle.net/2142/125233) publish
the VW1 deep-fluid data. Pre-injection swab samples (May 2011) of lower Mt. Simon zones 2–7 give Na 2.23, Cl 3.56,
Ca 0.56, Mg 0.10, K 0.059 mol/kgw (TDS 204 g/L, density 1.140, field pH 6.36). That is about 40% more saline than
the Liu et al. (2011) Indiana brine (Na 1.60, Cl 2.55, Ca 0.35). Upper Mt. Simon zones 8–9 match Liu closely
(Na 1.78, Cl 2.70, Ca 0.38). Stored as `data/ibdp_vw1_lower_mt_simon_brine.csv` and `..._upper_...csv`; systems
`lower_mt_simon_ibdp`, `argenta_ibdp`, `upper_mt_simon_ibdp`.

| Case | Dissolved C | Carbonate-mineral C | Main changes |
|---|---|---|---|
| Argenta, Liu | +43,994 mol | −1,950 | calcite +5,854, dolomite −3,902 |
| Argenta, IBDP | +36,708 (−17%) | −2,414 | calcite +14,408, dolomite −8,411 |
| Lower Mt. Simon, Liu | +268,822 | −757 | quartz +4,498, albite −919, siderite −742 |
| Lower Mt. Simon, IBDP | +219,973 (−18%) | −723 | quartz +5,631, albite −1,042, siderite −698 |

The saltier IBDP brine dissolves 17–18% less CO2 and, in the Argenta, drives 2.5× more calcite precipitation and
2× more dolomite dissolution.

**The step networks do not transfer to the IBDP brine.** Run on the IBDP-brine systems, the Liu-trained networks
accepted 0 of 1,200 (lower Mt. Simon) and 0 of 864 (Argenta) kinetic cells: every state was outside the training
box, so every cell went to PHREEQC and the error was zero. Range routing failed safe, but using the IBDP brine
means regenerating the training data (about 40 min of PHREEQC per unit) and recalibrating.
