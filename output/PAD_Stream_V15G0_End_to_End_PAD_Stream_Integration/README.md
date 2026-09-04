# PAD-Stream Version 15G-0

## Safeguarded end-to-end integration

Version 15G-0 connects the approved pressure, path, transport, conservative
map-back, timestep/retrace, well-memory, and nonlinear-difficulty branches into
one 365-day orchestration replay.

The accepted-state contract remains **predict-screen-correct**. Learned outputs
schedule or initialize work; exact TPFA, Peaceman, Pollock, nonlinear residual,
adaptive-timestep, and conservative-mass operators remain final authorities.

## Decision

- Integrity gates: **17/17**
- Deployment gates: **12/12**
- Diagnostic gates: **7/7**
- Status: **PASS**

## Integrated rollout

- End time: **365.0 days**
- Accepted physics steps: **350**
- Dense recurrent transitions: **349**
- Spatial transport/map-back refreshes: **24**
- Maximum pressure residual: **2.596e-10 m3/s**
- Maximum cumulative CO2 mass error: **7.153e-07 kg**
- Maximum map-back mass-closure error: **2.015e-16**
- Final grid saturation RMSE: **0.020231**
- Integrated gas-cut RMSE: **0.001943**
- Breakthrough timing error: **1.205 days**
- Restart maximum difference: **1.388e-17**

## Branch usage

- Pressure learned/fallback: **199 / 148**
- Path full-retrace avoidance: **75.31%**
- Map-back graph/fallback: **15 / 9**
- Timestep learned/fallback: **323 / 27**
- Gas-cut head selected/fallback: **98 / 251**
- Nonlinear preflight light/standard/full: **15 / 222 / 112**

## Interpretation

The milestone demonstrates that all approved Version 15 components can coexist
inside one safeguarded state machine without violating mass balance, pressure
closure, path legality, well constraints, restart identity, or solver safety.
It is an integration audit rather than the immutable release bundle.

## Next milestone

**Version 15G-1 — final Version 15 freeze, reproducibility manifest, and
advisor-ready baseline.**
