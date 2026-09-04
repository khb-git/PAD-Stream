# PAD-Stream V16E-0 — BL / Hybrid DP Evidence and Role Map

## Decision

V16E begins with architecture reconciliation, not model coding.

The purpose is to unify three transport lineages without allowing them to
silently redefine one another:

1. classical/finite-volume Buckley-Leverett transport teachers,
2. the existing BL PI-RNN family,
3. the frozen PAD-Stream recurrent Stage-4 evidence from V16D/EXP-CS1,

with Dykstra-Parsons retained as the controlled layered heterogeneity bridge.

## Frozen PAD-Stream authority chain

```text
SGSim / reservoir geology
        |
        v
finite-volume pressure
        |
        v
conservative Darcy flux
        |
        v
exact Pollock geometry + TOF
        |
        v
COMMON TRANSPORT INTERFACE
        |
        +-----------------------------+
        |              |              |
        v              v              v
 numerical BL       BL PI-RNN      frozen V16D
 teacher            proposal       EXP-CS1 baseline
        \              |              /
         \             |             /
          +------ evidence comparison-+
                       |
                       v
             transport selector
             (NOT chosen in E0)
                       |
                       v
          physics residual / bounds /
             inventory acceptance
                       |
                       v
          conservative path-to-grid
                       |
                       v
             accepted grid state
```

## Buckley-Leverett role

The natural bridge is total-flow time of flight. For the incompressible frozen
flow case, the streamline transport form is represented by

`dS/dt + d f(S)/d tau = 0`

with

`d tau = phi ds / |u_t|`.

The legacy BL family must first reproduce its original teacher in its original
coordinate system. Only then is the interface transformed to TOF while
preserving the same constitutive laws, front behavior, and acceptance metrics.

No compressible/capillary equation is implemented by a casual x→tau text
replacement. Its transformed residual must be derived and bound explicitly in
the adapter milestone.

## Hybrid Dykstra-Parsons role

DP is not a replacement for SGSim and it is not the 3-D connectivity solver.

It is the controlled layered benchmark that exposes:

- layer permeability/thickness/pore volume,
- rate allocation,
- local pore-volume injection clocks,
- breakthrough ordering,
- flux/PV-weighted aggregate response,
- classical DP severity,
- streamline-native F-Phi/Lorenz diagnostics.

Reference identities:

`sum_l F_l = 1`

`PVI_l = (F_l q_total t) / PV_l`

and, for a flux-weighted producer response,

`response_total = sum_l F_l response_l`.

The exact legacy rate-allocation weighting and DP coefficient definition remain
to be source-bound from the existing 8-layer benchmark before implementation.

## What V16E-0 does not decide

It does not decide whether the eventual PAD-Stream transport proposal engine is:

- the numerical teacher,
- one BL PI-RNN round,
- the frozen EXP-CS1 recurrent architecture,
- a Hybrid BL-DP branch,
- or an evidence-driven selector/hierarchy.

That decision must be made after identical-state teacher comparisons.

## Required next inventory

Before adapter coding, bind exact source/checkpoint identities and interface
metadata for:

- analytical BL teacher,
- FV BL incompressible,
- FV BL compressible,
- FV BL capillary,
- FV BL full compressible-capillary,
- BL PI-RNN Round 1,
- BL PI-RNN Round 2,
- BL PI-RNN Round 3,
- 8-layer DP benchmark,
- Hybrid DP PI-RNN / layer-RNN.

For every learned model, freeze:
inputs, outputs, units, teacher, physics loss, training domain, checkpoint/status.

## Firewall

EXP-CS1 remains closed.

Geology0029 may be referenced as historical evidence, but it may never again be
presented as an unseen test. Any new integrated BL/DP learning experiment must
prospectively define a new TRAIN/VALIDATION/LOCKED-TEST firewall.
