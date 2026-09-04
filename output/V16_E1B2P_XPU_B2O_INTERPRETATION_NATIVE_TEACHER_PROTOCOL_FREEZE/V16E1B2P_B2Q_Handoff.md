# V16E-1B2P-XPU — B2Q Native Godunov Verification Handoff

## What is certified

* The B2N conservative moving-fan derivation is preserved.
* The B2O autograd implementation cross-check is certified.
* Conservative and expanded forms agree to the float32 identity budget.
* Nc=0 algebraic nesting is certified.

## What is NOT certified

The B2O finite-difference residual of the saved 64-node fan targets is not accepted as a quantitative validation of the conservative PDE.

The frozen target is produced by:

    native 1601-cell Godunov state
      -> numerical front extraction
      -> interpolation to 64 xi nodes
      -> max(S,Sw_star)
      -> forced injector/tip endpoints
      -> only six retained times

## B2Q

Return to the exact source-native Godunov update. First verify the discrete finite-volume conservation identity using the actual update fluxes. Then perform a controlled ablation showing how each fan-processing operation changes the residual diagnostic.

No optimizer may be created in B2Q. Corrected Stage-2 training and B3 remain blocked.
