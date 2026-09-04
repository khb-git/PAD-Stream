# PAD-Stream V16E-0R — Corrected Development Path

## Status correction

V16E-0R supersedes the **interpretation**, not the files, of V16E-0A/B/C.

The prior provenance-search milestones remain immutable audit history. Their
assumption that the BL research lineage required recovery of separate historical
Round-1/2/3 artifacts is retired.

The actual Buckley-Leverett model lineage is:

1. Final incompressible PI-RNN
2. Final compressible PI-RNN
3. Final capillary PI-RNN
4. Final full compressible-capillary PI-RNN

Each source is the final model definition for that physics phase.

## Dykstra-Parsons lineage

The 8-layer case is a **controlled validation reference**, not the architecture.

The Hybrid lineage contains:

1. 10-parameter BL-DP PI-RNN
2. 12-parameter BL-DP PI-RNN
3. Synthetic N-layer DP formation generation

The 10-parameter conditioning vector is:

`[no, nw, swc, sor, mu_w, mu_o, phi, tD, xD_star, Sw_star]`

The 12-parameter conditioning vector is:

`[no, nw, swc, sor, mu_w, mu_o, phi, krw_max, kro_max, tD, xD_star, Sw_star]`

The additional variables are **relative-permeability endpoints**.

Absolute permeability `k_md` remains part of DP layer physics, `k*h` rate
allocation, and heterogeneity. It is not one of the 12 PI-RNN inputs.

## Saved weights

Historical trained weight/config files are currently unavailable.

Therefore:

- source code = authoritative final model definition;
- any model trained from these sources now = **new V16E reproduction**;
- every new reproduction requires a new experiment ID, manifest, checkpoint SHA,
  and validation record;
- no new reproduction may be described as recovery of an old checkpoint.

## Correct V16E sequence

### V16E-1A — BL reproduction protocol freeze

No training.

Freeze separately for the four final BL models:

- authoritative source SHA,
- native analytical/numerical teacher,
- training/validation semantics,
- input/conditioning vector,
- coordinate system,
- loss terms,
- expected checkpoint/config name for the new reproduction,
- deterministic seeds,
- acceptance metrics.

### V16E-1B — Native-coordinate BL reproduction

Retrain/reproduce the four final BL PI-RNNs in their original coordinate systems.

Compare:

- incompressible PI-RNN vs analytical BL,
- compressible PI-RNN vs conservative Godunov teacher,
- capillary PI-RNN vs capillary numerical teacher,
- full PI-RNN vs full compressible-capillary numerical teacher.

Do not transform to TOF yet.

### V16E-2 — BL-to-TOF transport transformation

Transform only after native reproduction is accepted.

The incompressible TOF form provides the simplest bridge.

Compressible/capillary/full residuals require explicit derivation; no blind
`x -> tau` substitution is allowed.

### V16E-3 — Hybrid DP reproduction and integration

Reproduce/test:

- 10-param Hybrid,
- 12-param Hybrid.

Use the 8-layer case as a controlled validation reference, then extend with the
synthetic generator.

### V16E-4 — Synthetic heterogeneity study

Exercise variable:

- layer count,
- DP severity,
- permeability distribution,
- thickness,
- porosity,
- Swc,
- relative-permeability endpoints,
- thief-zone structures.

This is the bridge from layered DP to full SGSim spatial heterogeneity.

### V16E-5 — Identical-state transport comparison

Under the same exact Pollock/TOF path states compare:

- exact/numerical transport teacher,
- validated BL PI-RNN / TOF branch,
- Hybrid BL-DP / TOF branch,
- frozen V16D recurrent Stage-4 baseline.

### V16E-6 — Evidence-driven transport strategy freeze

Choose only after V16E-5 whether PAD-Stream uses:

- one canonical proposal model,
- a physics-regime hierarchy,
- or multiple proposals with calibrated screen/fallback logic.

Pressure, Darcy, Pollock, inventory correction, and conservative map-back remain
physics authorities regardless of the learned transport proposal.

## Immediate next milestone

`V16E-1A — BL Native-Coordinate Reproduction Protocol Freeze`

This milestone defines the experiments but performs no training.
