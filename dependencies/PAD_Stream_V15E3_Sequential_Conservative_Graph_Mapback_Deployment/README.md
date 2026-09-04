# PAD-Stream Version 15E-3

Sequential conservative graph map-back deployment with one unique recurrent grid state.

## Decision

- Integrity gates: **19/19**
- Deployment gates: **7/7**
- Diagnostic gates: **3/5**
- Status: **PASS**

## Rollout contract

1. Sample the accepted 5x5x5 grid saturation/history onto the current corrected Pollock paths.
2. Run the frozen Version 15D-2 conditional PI-RNN for one-step path transport.
3. Apply the frozen 15D-2 bounded path-inventory correction for the canonical `d2_conservative` input branch.
4. Aggregate overlapping path observations onto one grid field with previous-grid fallback.
5. Forecast global CO2 inventory from current-state features only.
6. Run frozen Version 15E-2 graph inference, uncertainty screening, and exact self-consistent compressible mass projection.
7. Update saturation history exactly as the running maximum of accepted grid saturation.
8. Feed the accepted grid state—not a path interpolation—into the next transition.
9. Record producer gas-cut and breakthrough diagnostics for the Version 15F-1 handoff.

## Key results

- Sequential transitions: **24**
- Path updates: **4,320**
- Aggregate persistence RMSE: **0.042693**
- Aggregate deterministic map-back RMSE: **0.033343**
- Aggregate accepted 15E-3 RMSE: **0.033324**
- Final day-365 grid-state RMSE: **0.020231**
- Previous 15D-3 day-365 path drift: **0.106511**
- Inventory MAPE: **1.955%**
- Maximum accepted mass-closure error: **2.015e-16**
- Producer gas-cut RMSE: **0.378050**
- Predicted breakthrough: **45.211 days**
- Exact breakthrough: **115.750 days**
- Graph-selected transitions: **15**
- Deterministic fallback transitions: **9**

## Interpretation

Version 15E-3 validates the architectural hypothesis raised by Version 15D-3: the recurrent transport state must be unique on the grid. Exact pressure and corrected path geometry remain refreshed from the frozen reference in this milestone, but all saturation recurrence now passes through conservative grid map-back and saturation history is updated by its exact running-maximum rule. This removes normalized-TOF path-to-path interpolation from the deployed state loop.

The conservative map-back branch is approved on its core deployment gates. Producer gas-cut and breakthrough remain recorded diagnostics because global breakthrough and well-control memory are the explicit scope of Version 15F-1.

## Scope boundary

This is not yet the final end-to-end PAD-Stream rollout. Version 15F adds global timestep, retrace, breakthrough, control, and nonlinear-difficulty memory. Version 15G then integrates the approved pressure, path, transport, map-back, and recurrent-state branches.
