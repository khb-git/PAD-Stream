# PAD-Stream V16E-0D — WP0 Closure and Prospective Reproduction Handoff

## 1. WP0 is complete

The architecture-reconciliation phase is now closed.

Exact recovered authorities:

- Stage 1 incompressible BL PI-RNN source:
  `98d492e1e4a84e9d2c3ab99a631bf7d21d011b65bdd599e0ab3192d947b36e58`
- Stage 2 conservative compressible Godunov PI-RNN source:
  `1dda3155fc4183930448b689de52554454498b6787fcb323737b121ec0139397`
- Stage 3 capillary PI-RNN source:
  `dab8eade38ac08c819ac27d803c8f1bceca9722c4c37e82977dbef6e6232ae0f`
- Stage 4 full compressible-capillary Godunov PI-RNN source:
  `165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a`
- Canonical 8-layer DP physics source:
  `45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6`

The common total-flow TOF interface and exact pressure/Darcy/Pollock authorities
remain frozen from V16E-0.

## 2. Historical learned artifacts are unavailable

After searching the portable project, sibling PyCharm projects, and the file
library, the exact historical learned identities remain unavailable for:

- BL Round 1 — earliest validated PI-RNN,
- BL Round 2 — expanded/conditioned PI-RNN,
- BL Round 3 — most complete BL PI-RNN,
- Hybrid DP PI-RNN / layer-RNN.

This is now a formal provenance statement, not an unresolved temporary guess.

## 3. Scientific consequence

The missing checkpoints do **not** invalidate the dissertation lineage.

They change how the next experiment is described.

We may reproduce/train models from the exact recovered Stage sources, but every
new trained artifact must be labeled as a **new V16E prospective reproduction**.

A new checkpoint may never be described as:

- the recovered historical Round 1 checkpoint,
- the recovered historical Round 2 checkpoint,
- the recovered historical Round 3 checkpoint,
- or the recovered historical Hybrid DP checkpoint.

## 4. Revised integration strategy

The next branch should proceed in this order:

### V16E-1A — BL source-reproduction protocol freeze

Before training:

- define which Stage source(s) are reproduced,
- bind original teacher/target semantics,
- define training/validation cases,
- define units and coordinate transformation to TOF,
- define acceptance metrics,
- assign new experiment IDs,
- define new checkpoint naming and SHA policy.

No geology0029 reuse as a new unseen test.

### V16E-1B — Reproduce original-coordinate BL models

Train new checkpoints from the exact recovered sources in their native
1-D coordinate systems first.

Goal:

`recovered source -> reproduced teacher agreement`

This establishes reproducibility without claiming historical-checkpoint recovery.

### V16E-1C — Total-flow TOF adapter

Only after native-coordinate reproduction passes:

`x / x_D formulation -> total-flow TOF interface`

The constitutive physics must remain unchanged.

Compressible and capillary branches require explicitly derived transformed
residuals rather than a blind coordinate substitution.

### V16E-2 — New Hybrid BL-DP branch

Use the recovered 8-layer DP physics source as the exact heterogeneity teacher:

- layer k/h/PV,
- rate allocation,
- local PVI,
- breakthrough ordering,
- flux-weighted aggregation.

If a learned Hybrid DP model is desired, it becomes a **new V16E model**
trained prospectively against this exact DP/BL teacher.

### V16E-3 — Compare with frozen PAD-Stream transport

Compare under identical path states:

- reproduced BL/TOF proposal,
- new Hybrid BL-DP proposal if built,
- frozen V16D/EXP-CS1 evidence baseline,
- exact numerical teacher.

Then choose the canonical proposal hierarchy from evidence.

## 5. Governing deployment rule remains unchanged

```text
learned proposal
      |
      v
physics residual / calibrated screen
      |
      +---- fail ---> exact teacher / fallback
      |
      v
bounded inventory correction
      |
      v
conservative path-to-grid map-back
      |
      v
accepted unique grid state
```

Pressure, Darcy flux, Pollock kinematics, inventory closure, and conservative
map-back remain physics authorities.

## 6. What is authorized now

Authorized:

- prospective BL reproduction protocol design,
- TOF adapter design from exact recovered BL sources,
- DP physics adapter/design using the recovered v14 source,
- new Hybrid BL-DP model design with a new experiment identity.

Not yet authorized:

- training before the new protocol is frozen,
- claiming any new checkpoint is a recovered historical Round checkpoint,
- reuse of geology0029 as a new unseen test.
