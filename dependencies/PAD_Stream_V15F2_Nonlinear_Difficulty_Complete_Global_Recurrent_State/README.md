# PAD-Stream Version 15F-2

## Nonlinear-difficulty and complete global recurrent state

Version 15F-2 freezes the approved 15F-0 timestep/retrace memory and 15F-1
breakthrough/well-control memory, then attaches three compact workload heads:
next nonlinear iterations, next total pressure fixed-point iterations, and retry
probability.

## Decision

- Integrity gates: **18/18**
- Deployment gates: **10/10**
- Diagnostic gates: **5/5**
- Status: **PASS**

## Held-out performance

- Test nonlinear RMSE: **0.423734** versus persistence **0.600925**
- Test pressure-workload RMSE: **2.035920** versus persistence **2.801289**
- Test retry recall: **100.00%**
- Test retry precision: **64.29%**
- Test retry AUC: **0.997942**
- Test initial-budget coverage: **100.00%**
- Test initial reserved-budget reduction: **26.48%**
- Unsafe budget misses without exact escalation: **0**

## Safety contract

The predicted budgets are initial allocations, not convergence limits. Exact
pressure and nonlinear residual tests continue unchanged. Any budget miss,
uncertain state, well-control preflight, or predicted retry risk escalates to
the full classical solver. The learned state never certifies convergence.

## Complete Version 15F state

The packaged complete state now carries:

1. 15F-0 adaptive timestep and retrace memory;
2. 15F-1 gas-cut, breakthrough, and well-control memory;
3. 15F-2 nonlinear workload, retry risk, and solver-preflight memory.

The next milestone is Version 15G-0 end-to-end integration of the approved
pressure, path, transport, map-back, and complete global recurrent-state branches.
