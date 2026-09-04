# V16E-1B2AE-XPU — B2AF Execution-Preflight Handoff

## Prospective experiment

`V16E-BLREP-COMP-XPU-005`

## Frozen implementation

* derivative engine: `CHUNKED_BATCHED_VJP`
* cotangent chunk: 16
* microbatch: 128
* logical batch: 8192
* epochs: 800
* seed: 1337

## Fresh training

COMP-XPU-005 must start from a fresh seed=1337 model initialization. The frozen COMP-XPU-004 checkpoint is comparison/provenance authority only and must never be used as the COMP-XPU-005 initializer.

## Gradient accumulation

* 8192-profile logical chunk: 64 microbatches, scale each loss by 128/8192
* 3328-profile final logical chunk: 26 microbatches, scale each loss by 128/3328
* 90 microbatches/epoch
* 2 optimizer steps/epoch
* 1600 optimizer steps over 800 completed epochs

## Optimizer

`torch.optim.Adam(model.parameters(), lr=1.0e-3, foreach=False)`

No scheduler, mixed precision, or gradient clipping.

## Resume

Atomic checkpoint after every completed epoch. Resume only from an exact hash-matching completed-epoch checkpoint with model, optimizer, history, and RNG states. No mid-batch or partial-gradient resume.

## B2AF

Run one scratch production-sized logical batch (8192 profiles / 64 microbatches), perform exactly one Adam step, save and reload an atomic scratch checkpoint, and verify model/optimizer/RNG restoration. The scratch weights are never allowed to seed COMP-XPU-005.

Full COMP-XPU-005 training remains blocked until the rehearsal is certified and a separate authorization milestone passes. B3 remains blocked.
