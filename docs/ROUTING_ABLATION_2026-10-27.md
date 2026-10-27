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
