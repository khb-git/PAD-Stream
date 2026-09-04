# V16E-1B2X-XPU — B2Y Warmed Benchmark Handoff

## B2W is certified

The exact corrected graph completed with finite gradients and no weight mutation. Its synchronized profile showed a very large cost relative to the matched first-order control.

## Why B2W is not yet the steady-state baseline

The corrected profile ran first. Its model-forward timing was 2.043 s, whereas the later matched-control forward was 0.042 s on the same model and reference batch. B2X does not guess the runtime cause, but this directly shows first-use/runtime state affected the measurement.

## B2Y

Use microbatch 128 and the exact same 128 B2U/B2W rows.

Corrected graph:
  * 1 unmeasured warm-up
  * 3 uninstrumented measured backward iterations

Matched control:
  * 1 unmeasured warm-up
  * 3 uninstrumented measured backward iterations

Then perform one warmed synchronized corrected stage profile.

No optimizer and no weight update. Only after B2Y should we decide whether to optimize the recurrent derivative engine or freeze the execution contract.

COMP-XPU-005 full training and B3 remain blocked.
