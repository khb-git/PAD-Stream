# V16E-1B2AB-XPU — B2AC Chunked Batched-VJP Handoff

## B2AA certified result

The one-call 64-cotangent batched VJP failed at microbatch 128 with:

`RuntimeError: level_zero backend failed with error: 40 (UR_RESULT_ERROR_OUT_OF_RESOURCES)`

This is preserved as a runtime-resource result. Do not reinterpret it as proof that every `is_grads_batched=True` configuration is unsupported.

## B2AC route

Test cotangent chunk sizes:

* 2
* 4
* 8
* 16
* 32

Known endpoints:

* chunk 1 = loop baseline semantics
* chunk 64 = B2AA runtime-resource failure

Every candidate must use a fresh subprocess/XPU context.

## Equivalence first

For every runtime-successful candidate compare N_xi, N_tD, N_X, corrected residual, physics loss, total loss, and every parameter gradient to the exact loop baseline using only the frozen float32 epsilon-derived budget.

Only equivalent candidates receive one warm-up plus three measured repeats.

No optimizer, no weight update, no fallback, no OOD, no TOF.

B2AC does not adopt a candidate. B2AD interprets the measured set.

COMP-XPU-005 full training and B3 remain blocked.
