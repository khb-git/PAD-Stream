# V16E-1B2AD-XPU — B2AE Execution-Preflight Handoff

## Adopted derivative implementation

* Engine: chunked batched VJP
* Cotangent chunk size: 16
* Reference training microbatch: 128

The adoption is implementation-only. B2AC certified derivative, corrected residual, losses, and parameter-gradient equivalence to the exact loop baseline.

## Performance basis

* Loop baseline median: 10.102323 s
* Chunk-16 median: 7.866888 s
* Loop/chunk-16 ratio: 1.284158x
* Chunk-16 throughput: 16.270730 profiles/s

Chunk 16 was the lowest measured median in B2AC. This is not a statistical superiority claim over chunk 8 or 32.

## Diagnostic execution geometry

* Train profiles: 11520
* Logical batch: 8192
* Microbatch: 128
* Microbatches/epoch: 90
* Target epochs: 800
* Diagnostic projection: 0.196672 h/epoch, 6.555740 days/800 epochs

The projection is not a runtime promise.

## Next

B2AE must freeze the exact COMP-XPU-005 execution-preflight contract, including optimizer, accumulation, checkpoint/resume, and fail-closed training-runner behavior. Full training remains blocked until B2AE passes.

B3 remains blocked.
