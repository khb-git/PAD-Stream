# V16E-1B2R-XPU — B2S Feasibility Handoff

## Scientific status

The corrected conservative moving-fan residual is now scientifically ready for a controlled Stage-2 experiment. The native Godunov teacher is exactly conservative to machine precision in B2Q, and the processed fan finite-difference artifacts have been separated from the solver balance.

## Prospective experiment

Reserved ID: **V16E-BLREP-COMP-XPU-005**

Only scientific change relative to COMP-XPU-004: replace the old characteristic physics loss with the corrected conservative moving-fan residual.

## Do not train yet

The corrected residual requires differentiating the recurrent network with respect to xi, tD, and xD_star and then backpropagating through those derivatives. B2S must benchmark this graph on Intel XPU with NO optimizer and NO weight update.

Candidate microbatches: 1, 2, 4, 8, 16.

After B2S, freeze the operational microbatch and only then authorize the fresh 800-epoch COMP-XPU-005 training runner.

B3 remains blocked.
