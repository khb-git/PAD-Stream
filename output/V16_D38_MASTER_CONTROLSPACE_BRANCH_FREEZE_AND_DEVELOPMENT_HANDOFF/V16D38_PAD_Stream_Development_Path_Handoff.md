# PAD-Stream V16D-38 — Master Branch Freeze and Development-Path Handoff

## 1. Decision

**The V16D control-space / EXP-CS1 branch is complete and should be frozen.**

There is no scientific reason to continue tuning EXP-CS1. The final
geology0029 OOD set has already been consumed, and the final model performed
without aggregate validation degradation:

- OOD RMSE = **4.235076137538e-03**
- OOD MAE = **1.733692782761e-03**
- OOD RMSE / validation RMSE = **0.972040**
- OOD MAE / validation MAE = **0.987730**

The next work should therefore extend the PAD-Stream architecture rather than
revisit this experiment.

---

## 2. What V16D completed

V16D established a controlled heterogeneous SGSim learning experiment around
the Stage-4 transport component.

### Frozen physical backbone

**SGSim geology -> finite-volume pressure -> conservative Darcy fluxes ->
exact Pollock streamlines -> TOF/transport coordinates**

This backbone remains physics-defined.

### Frozen recurrent transport experiment

EXP-CS1 uses a 201-node, nine-channel streamline sequence and a two-layer
LSTM transport predictor.

It has been tested across:

- TRAIN geology realizations 0026 and 0027,
- VALIDATION geology0028,
- independent locked-OOD geology0029,
- injection rates 350 / 500 / 650 t/day,
- producer BHP 1800 / 2000 / 2200 psi.

The final unseen-geology result is slightly better in aggregate than the
frozen validation reference.

---

## 3. What should NOT be done next

The following paths are closed under EXP-CS1:

- retraining EXP-CS1,
- trying another EXP-CS1 checkpoint on geology0029,
- changing the nine predictor channels and retesting geology0029,
- changing normalization and retesting geology0029,
- introducing a new loss or threshold and using geology0029 to judge it,
- treating geology0029 as unseen in a later experiment.

Any new learning experiment needs a new prospectively locked test realization.

---

## 4. Remaining revised PAD-Stream development path

### Next integration branch — BL / Hybrid DP transport integration

The next architectural task should be to integrate the previously developed:

1. **Buckley-Leverett PI-RNN transport formulation**, and
2. **Hybrid Dykstra-Parsons PI-RNN heterogeneity formulation**

into the frozen PAD-Stream streamline transport architecture.

This should be treated as a **new integration branch**, not a modification of
EXP-CS1.

Recommended goals:

- preserve Pollock as authoritative kinematics,
- preserve exact pressure / Darcy physics,
- preserve the V16D frozen control-space branch as comparison evidence,
- define how BL physics-informed transport and DP heterogeneity conditioning
  enter the Stage-4 transport layer,
- distinguish learned transport physics from geological-state descriptors,
- prospectively define any new TRAIN / VALIDATION / LOCKED-OOD split before
  evaluating the new learning formulation.

### After BL / DP integration — IBDP field-transfer branch

Once the revised PAD-Stream architecture is integrated and frozen, proceed to
the IBDP work as the larger field-model transfer stage.

The IBDP branch should be treated as a new scale/geometry/domain-transfer
problem rather than as another iteration of EXP-CS1.

---

## 5. Recommended milestone sequence

### V16E-0 — BL / DP Integration Contract
Freeze the role of:
- BL PI-RNN,
- Hybrid DP PI-RNN,
- Pollock,
- pressure / Darcy physics,
- Stage-4 transport coordinates,
- recurrent/global state components.

No training.

### V16E-1 — Frozen BL Transport Adapter
Connect the previously validated BL PI-RNN formulation to the 201-node
streamline transport interface without changing the frozen V16D evidence.

### V16E-2 — Frozen Hybrid DP Heterogeneity Adapter
Introduce the DP hybrid heterogeneity representation explicitly and define
where it conditions transport.

### V16E-3 — Integrated BL+DP Stage-4 Experiment Contract
Define new datasets, split firewall, normalization, losses, metrics, and new
locked test identity before training.

### V16E-4+ — Train / Validate / One-Touch Test
Execute the new integrated transport experiment prospectively.

### V16F — Full PAD-Stream Architecture Freeze
Freeze the complete revised architecture after BL/DP integration.

### Field-transfer branch — IBDP
Move the frozen architecture to the IBDP geological/reservoir model.

---

## 6. Architecture after V16D

```text
SGSim geology
      |
      v
Finite-volume pressure
      |
      v
Conservative Darcy fluxes
      |
      v
Exact 3-D Pollock streamlines
      |
      v
TOF / transport coordinates
      |
      +-----------------------------+
      |                             |
      v                             v
Frozen EXP-CS1 evidence       Next V16E integration
(control-space recurrent)     BL PI-RNN + Hybrid DP PI-RNN
      |                             |
      +-------------+---------------+
                    |
                    v
        Integrated Stage-4 transport
                    |
                    v
        Conservative map-back / state
                    |
                    v
        Global recurrent PAD-Stream
                    |
                    v
              IBDP transfer
```

---

## 7. Scientific interpretation of where we are

The important shift after V16D is that **heterogeneous SGSim transport
generalization is no longer an untested architecture idea**. It now has a
prospectively separated TRAIN / VALIDATION / locked-OOD experiment behind it.

The next dissertation-development question is therefore no longer:

> Can a recurrent Stage-4 transport model work on the heterogeneous SGSim
> PAD-Stream representation?

V16D provides evidence that it can within the frozen experiment.

The next question becomes:

> How do the previously developed Buckley-Leverett physics-informed transport
> and Hybrid Dykstra-Parsons heterogeneity formulations become explicit,
> integrated components of the full PAD-Stream architecture?

That is the natural handoff into V16E.
