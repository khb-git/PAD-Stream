# PAD-Stream Version 15F-0

## Global recurrent timestep and retrace state

Version 15F-0 introduces one compact GRU state over the accepted simulator
history. The recurrent state has two deployable proposal heads:

1. next adaptive timestep;
2. total-flow/gas-path retrace load at path-update snapshots.

Both remain inside the PAD-Stream **predict-screen-correct** contract. The GRU
never overrides the classical timestep acceptance controller, and a learned
cache-only decision never bypasses the exact path-cache/Pollock authority when
confidence is inadequate.

## Decision

- Integrity gates: **17/17**
- Deployment gates: **10/10**
- Diagnostic gates: **4/4**
- Status: **PASS**

## Timestep proposal

- Accepted-step records: **350**
- Test persistence RMSE: **0.292863 days**
- Test screened-GRU RMSE: **0.189993 days**
- Test screened-GRU MAE: **0.068196 days**
- Test RMSE reduction: **35.13%**
- Timestep proposals selected: **323**
- Confidence fallbacks: **27**

## Retrace memory

A high-retrace event is defined as at least 18%
of the total-flow family, gas family, or gas family membership requiring a new
or full-retrace update.

- Audited path snapshots: **24**
- Test retrace-fraction RMSE: **0.065302**
- Unsafe cache-only decisions: **0**
- Full-family retraces avoided: **6**
- Avoided full-family fraction: **25.00%**
- OOD full-retrace fallbacks: **5**

## Recurrent restart

The day-195 hidden state reproduces the uninterrupted hidden
trajectory, timestep outputs, and retrace outputs exactly.

## Scope boundary

- Producer gas cut, breakthrough flags, and breakthrough targets are excluded.
  Breakthrough and well-control memory are Version 15F-1.
- The explicit nonlinear-difficulty state/head is Version 15F-2.
- Version 15G will connect this recurrent state to the approved pressure, path,
  transport, and conservative map-back branches in the final end-to-end loop.
