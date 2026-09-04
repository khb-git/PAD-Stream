# PAD-Stream V16E-1A — Execution Handoff

## Protocol status

This milestone freezes the native-coordinate reproduction contract for the four
final Buckley-Leverett PI-RNN phases.

No model has been trained in V16E-1A.

## Reproduction order

1. `V16E-1B1` — incompressible
2. `V16E-1B2` — compressible conservative-Godunov
3. `V16E-1B3` — capillary
4. `V16E-1B4` — full compressible-capillary conservative-Godunov

Each phase is certified before the next one begins.

## Why the original coordinates are preserved

The goal of V16E-1B1 through V16E-1B4 is source reproducibility, not PAD-Stream
integration.

The model must first reproduce the teacher it was designed to solve.

Only after the four native-coordinate reproductions are understood do we begin
the BL-to-TOF transformation.

## Holdout semantics

The sources use an 80/20 shuffled profile split with seed 1337.

For V16E reproduction this is preserved because the immediate question is
source-faithful reproduction.

It is not an independently locked OOD test and no claim of OOD geology or
independent generalization may be attached to it.

## Stage-3 and Stage-4 metadata

The final executable conditioning interfaces are:

Stage 3:
`[no, nw, swi, sor, mu_w, mu_o, phi, tD, xD_front, Sw_star,
  inv_Pec, lambda_bc, log10(mu_w/mu_o)]`

Effective dimension: **13**.

Stage 4:
`[no, nw, swi, sor, mu_w, mu_o, phi, tD, xD_front, Sw_star,
  inv_Pec, lambda_bc, Nc, log10(mu_w/mu_o)]`

Effective dimension: **14**.

The old config writers serialize stale metadata from the earlier 12-field
TrainConfig tuple. The final source files are not silently edited. The NEW V16E
reproduction manifests will record the actual executable interfaces.

## Accuracy thresholds

V16E-1A intentionally does not invent a numerical pass threshold.

The source-defined teacher metrics, front diagnostics, mass behavior, saturation
bounds, and nesting checks are archived during reproduction. Any later numerical
threshold must be frozen prospectively before it is used as a decision gate.

## Immediate next milestone

`V16E-1B1 — Final Incompressible BL PI-RNN Native-Coordinate Reproduction`

That milestone may train a NEW V16E reproduction checkpoint from the exact
frozen Stage-1 source. It does not transform to TOF.
