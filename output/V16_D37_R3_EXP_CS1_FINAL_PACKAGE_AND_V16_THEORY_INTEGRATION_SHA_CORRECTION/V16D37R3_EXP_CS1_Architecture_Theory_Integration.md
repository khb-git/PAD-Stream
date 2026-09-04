# PAD-Stream Version 16 — EXP-CS1 Architecture and Theory Integration

## 1. Scientific status

**EXP-CS1 is complete and closed.**

The final locked-OOD geology (`0029`) has been opened exactly once, evaluated
with the single validation-selected checkpoint, interpreted without reopening
the arrays, and permanently consumed as the final test set.

No further retraining, checkpoint selection, architecture changes, feature
changes, normalization changes, threshold tuning, or OOD-informed model
selection are permitted under EXP-CS1.

Any new learning experiment requires a new independently locked test set.

---

## 2. PAD-Stream computational architecture represented by EXP-CS1

The control-space recurrent Stage-4 experiment sits downstream of the
physics-based PAD-Stream kinematic backbone:

1. **SGSim heterogeneous geology**
   - 3-D geological property field.
   - Dissertation-base heterogeneity source.

2. **Finite-volume pressure**
   - Exact physics state construction.
   - Produces pressure consistent with the frozen reservoir controls.

3. **Conservative Darcy face fluxes**
   - Derived from the pressure solution.
   - Preserve the finite-volume flow balance.

4. **Exact 3-D Pollock streamlines**
   - Pollock remains the **authoritative kinematic representation**.
   - Streamline geometry and time-of-flight are not replaced by the neural model.

5. **Transport-coordinate construction**
   - Each sample is a 201-node Pollock streamline sequence.
   - The recurrent model operates in streamline/TOF coordinates.

6. **C20 nine-channel predictor interface**
   - `xi`
   - `pollock_tau_hat`
   - `adv_tau_hat`
   - `log10_Kh`
   - `log10_Kz_over_Kh`
   - `porosity`
   - `pressure_z`
   - `target_time_hat`
   - `target_eta_sequence`

7. **EXP-CS1 recurrent Stage-4 transport model**
   - LSTM(64)
   - LSTM(64)
   - TimeDistributed Dense(1, sigmoid)
   - Saturation rescaling to `[0.2, 0.8]`
   - 52,033 trainable parameters.

The learned component predicts **Stage-4 saturation along the frozen Pollock
streamline coordinate**. It does not replace the pressure solve, conservative
Darcy flux construction, or Pollock tracing.

---

## 3. Role hierarchy of auxiliary quantities

The final EXP-CS1 predictor contract preserves the following hierarchy:

- **Pollock:** authoritative kinematics.
- **ADV:** auxiliary predictor coordinate.
- **FMM:** not used as an EXP-CS1 predictor.
- **M_face:** physics sidecar, not predictor.
- **Rate/BHP:** no direct predictor channels; their influence enters through the
  physical state and transport coordinates.

This separation is important to the PAD-Stream architecture because it keeps
the recurrent transport surrogate embedded inside a physics-defined flow and
kinematic system rather than allowing the learned model to redefine the
streamline geometry.

---

## 4. Generalization firewall

The unit of generalization is a **complete Foundation Case**:

> one geology realization + one injection-rate / producer-BHP pair.

The frozen split is:

- **TRAIN:** geologies 0026 and 0027, 18 complete cases.
- **VALIDATION:** geology 0028, 9 complete cases.
- **LOCKED OOD TEST:** geology 0029, 9 complete cases.

Control factorial:

- Injection rate: 350, 500, 650 t/day.
- Producer BHP: 1800, 2000, 2200 psi.
- Target times: 30, 60, 100, 150, 250, 365, 500, 750, 1000 days.

Normalization was fit on TRAIN only. Validation was used only for checkpoint
selection. Geology0029 was excluded from training, normalization, architecture
selection, feature selection, checkpoint selection, and threshold tuning.

---

## 5. Frozen recurrent model

Selected checkpoint:

- Best epoch: **73**
- Checkpoint SHA-256: `dc586da13e9fd7ce0b51cc661ba73edc8ab0f897d2f961112944504b13d1ed13`
- Architecture SHA-256: `4304519d7c41b231f300535cef5daacd2525e395413addc883e66e7310096920`

Frozen validation metrics:

- MSE: **1.898255084950e-05**
- RMSE: **4.356896928951e-03**
- MAE: **1.755229556989e-03**

---

## 6. Final locked-OOD result

The final geology0029 evaluation includes all:

- 9 control cases,
- 9 target times,
- 1,078 streamlines per case,
- 201 Pollock nodes per streamline,

for **17,550,918 saturation values**.

Aggregate OOD performance:

- MSE: **1.793586989075e-05**
- RMSE: **4.235076137538e-03**
- MAE: **1.733692782761e-03**
- Mean signed error: **2.823970512549e-04**
- Maximum absolute error: **1.350326836109e-01**

Generalization ratios:

- OOD RMSE / validation RMSE: **0.972040**
- OOD MAE / validation MAE: **0.987730**

Therefore the final unseen-geology aggregate RMSE is
**2.796% lower**
than the frozen validation RMSE, and the aggregate MAE is
**1.227% lower**
than the frozen validation MAE.

This is evidence of successful generalization in the **predeclared EXP-CS1
experiment**, not evidence that every unseen geological realization will have
equal or lower error.

---

## 7. Control-space observations

### Injection rate

| Rate (t/day) | RMSE | MAE |
|---:|---:|---:|
| 350 | 4.996167938798e-03 | 2.018917935558e-03 |
| 500 | 3.927478224089e-03 | 1.633166432870e-03 |
| 650 | 3.663445154344e-03 | 1.548993979855e-03 |

Within geology0029, both RMSE and MAE decrease as rate increases across the
three preregistered rate levels. This is a **post-OOD descriptive observation**
and cannot be used to modify EXP-CS1.

### Producer BHP

| Producer BHP (psi) | RMSE | MAE |
|---:|---:|---:|
| 1800 | 4.454372178418e-03 | 1.743562322272e-03 |
| 2000 | 4.156254988550e-03 | 1.696855351640e-03 |
| 2200 | 4.085550469463e-03 | 1.760660674371e-03 |

RMSE decreases across these BHP levels, but MAE is not strictly monotonic.
Accordingly, the BHP response should be treated as a descriptive interaction
with geology/control state rather than a simple monotonic model property.

---

## 8. Case-level envelope

Lowest-RMSE OOD case:

- `V16D_Foundation_Case_0029_R650_B2000`
- RMSE = **3.586716866568e-03**

Highest-RMSE OOD case:

- `V16D_Foundation_Case_0029_R350_B1800`
- RMSE = **5.299040797022e-03**

All cases remain in the final evaluation. No case, time, streamline, node, or
control condition was removed.

---

## 9. Physics-diagnostic interpretation

The preregistered post-prediction diagnostics remain part of the EXP-CS1
evidence package:

- Saturation bounds relative to `Swc = 0.2` and `1 - Sor = 0.8`.
- Injector-node boundary error relative to `Sw = 0.8`.
- Temporal negative-difference fraction using threshold `-1e-8`.
- Streamline spatial positive-difference fraction using threshold `+1e-8`.

These diagnostics are **descriptive scientific diagnostics**, not post-OOD
accept/reject criteria invented after seeing the test result.

---

## 10. Scientific claim boundary

### Supported claim

Within the frozen EXP-CS1 protocol, the recurrent Stage-4 transport model
generalized from TRAIN geologies 0026–0027, through validation geology0028, to
the independently locked geology0029 across the complete 3×3 rate/BHP control
space **without aggregate RMSE or MAE degradation relative to the frozen
validation reference**.

### Claim not supported by this experiment alone

EXP-CS1 does **not** establish universal generalization to arbitrary reservoir
geologies. The final OOD partition contains one independent geological
realization. Broader geological claims require additional prospectively locked
realizations or a new independent field-transfer protocol.

---

## 11. Version 16 architectural meaning

EXP-CS1 provides evidence that the PAD-Stream Stage-4 recurrent transport layer
can operate across a control factorial and transfer to one unseen SGSim
geological realization while preserving the architecture's central physics
division:

**geology → exact pressure → conservative Darcy flux → exact Pollock
kinematics → TOF/transport coordinates → recurrent saturation prediction**

The neural model therefore remains a transport surrogate **inside** a
physics-defined streamline simulator rather than becoming a replacement for
the flow solver or streamline geometry.

---

## 12. Packaging provenance correction

The first three V16D-37 packaging attempts inherited this malformed expected
D31D summary hash:

`a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3e`

It is **65 hexadecimal characters**, so it cannot be a SHA-256 digest.

The correct D31D summary SHA-256 is:

`a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3`

It is exactly **64 hexadecimal characters** and is the value already used by
the frozen upstream D32/D33/D34 lineage.

V16D-37-R3 restores strict exact-SHA checking with the correct digest and adds
a format gate requiring every frozen SHA literal to be exactly 64 hexadecimal
characters. No model, OOD result, prediction, metric, or scientific conclusion
was changed.

---

## 13. Experiment closure

EXP-CS1 is now immutable.

- Geology0029 is permanently consumed as its final locked-OOD test.
- No EXP-CS1 retraining is authorized.
- No alternate checkpoint may be evaluated on geology0029.
- No feature, normalization, architecture, loss, or threshold change may be
  evaluated against geology0029 as an unseen test.
- Any future learning experiment must use a new independently locked test set.

This record should be cited together with the V16D-37 experiment manifest and
the frozen D35/D36-R1 SHA-256 lineage.
