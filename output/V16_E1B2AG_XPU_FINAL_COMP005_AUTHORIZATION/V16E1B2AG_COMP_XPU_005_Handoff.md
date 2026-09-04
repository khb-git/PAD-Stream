# V16E-1B2AG-XPU — COMP-XPU-005 Production Handoff

## Final authorization

`V16E-BLREP-COMP-XPU-005` is authorized to run after B2AG passes.

## Fresh start is mandatory

* Seed: 1337
* Do not load COMP-XPU-004 weights
* Do not load B2AF scratch weights
* Do not load any prior Stage-2 checkpoint

After the production run begins, resume is permitted only from an atomic completed-epoch checkpoint created by the authorized COMP-XPU-005 runner with exact matching hashes.

## Frozen production mechanics

* derivative engine: CHUNKED_BATCHED_VJP
* cotangent chunk: 16
* microbatch: 128
* logical batch: 8192
* 90 microbatches/epoch
* 2 optimizer steps/epoch
* 800 epochs
* 1600 optimizer steps total
* Adam(lr=1e-3, foreach=False)
* atomic checkpoint every completed epoch

## B2AF evidence

* 8192-profile rehearsal wall time: 503.660696 s
* observed rehearsal throughput: 16.264918 profiles/s
* accumulated gradient norm: 5.658700e+00
* model reload exact: True
* optimizer reload exact: True
* RNG reload exact: True

The B2AF scratch checkpoint is permanently prohibited as a production initializer or resume source.

## Next

Materialize the exact provenance-bound COMP-XPU-005 production runner and execute the fresh 800-epoch run. After completion, perform a separate Stage-2 scientific comparison/closure milestone before B3.
