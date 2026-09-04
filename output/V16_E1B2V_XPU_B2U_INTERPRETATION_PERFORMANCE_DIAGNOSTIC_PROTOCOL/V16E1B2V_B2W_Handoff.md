# V16E-1B2V-XPU — B2W Performance Diagnostic Handoff

## B2U certified result

* microbatch 32: PASS
* microbatch 64: PASS
* microbatch 128: PASS
* microbatch 256: FAIL, frozen class RUNTIME_ERROR

Microbatch 128 is the largest proven-feasible tested value. It is not declared the hardware ceiling or final training value.

## Why full training is still blocked

The B2U isolated timing projection at microbatch 128 remains operationally large for 800 epochs. The projection is diagnostic only, but warrants profiling of the exact second-order derivative engine before committing to the full run.

## B2W

Profile the exact B2S corrected graph at microbatch 128 with no optimizer and no weight update. Time forward, local recurrent derivatives, corrected residual algebra, non-physics losses, backward, and synchronization. Also run a matched first-order/non-physics backward control.

Preserve the exact microbatch-256 error text from B2U; do not guess whether it was memory, runtime support, or another device/runtime condition.

COMP-XPU-005 full training and B3 remain blocked.
