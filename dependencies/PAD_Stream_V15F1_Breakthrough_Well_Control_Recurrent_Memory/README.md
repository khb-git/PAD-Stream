# PAD-Stream Version 15F-1

## Breakthrough and well-control recurrent memory

Version 15F-1 freezes the approved Version 15F-0 GRU encoder and attaches
compact well-memory heads for producer gas cut, breakthrough hazard, and
injector control mode. The heads consume only the current accepted state and
past recurrent memory.

The learned outputs are **warm starts and event warnings**. Exact Peaceman well
equations, phase-potential fluxes, and active BHP/mass-rate constraints remain
mandatory final authorities.

## Decision

- Integrity gates: **18/18**
- Deployment gates: **10/10**
- Diagnostic gates: **5/5**
- Status: **PASS**

## Producer gas-cut memory

- Held-out persistence RMSE: **0.007359**
- Held-out screened recurrent RMSE: **0.002741**
- Held-out RMSE reduction: **62.75%**
- Breakthrough-window RMSE reduction: **63.39%**
- Version 15E-3 snapshot gas-cut RMSE: **0.378050**
- Version 15F-1 snapshot gas-cut RMSE: **0.002531**

## Breakthrough memory

- Exact interpolated breakthrough: **116.169 days**
- Recurrent predicted breakthrough: **117.375 days**
- Absolute timing error: **1.205 days**
- Warning lead time: **10.125 days**
- Breakthrough hazard is monotone by construction.

## Well-control memory

- Screened control-mode accuracy: **100.00%**
- True control switches: **2**
- Switches sent to exact preflight: **2**
- Unsafe no-preflight decisions: **0**
- Exact-control preflight fraction: **7.45%**

## Recurrent restart

The saved day-195 Version 15F-0 hidden state reproduces the
uninterrupted 15F-1 gas-cut, breakthrough, and control outputs exactly.

## Scope boundary

- Exact well equations and control switching remain mandatory corrections.
- The controlled 5x5x5 trajectory contains only two injector mode switches and
  one breakthrough transition; broader multi-case training is deferred.
- Explicit nonlinear-difficulty memory is Version 15F-2.
- Version 15G will integrate the approved pressure, path, transport, map-back,
  and recurrent-state branches.
