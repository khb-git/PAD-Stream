# V16E-1B2T-XPU — B2U Extended Throughput Handoff

## Certified B2S result

Microbatches 1, 2, 4, 8, and 16 all execute the exact corrected-residual create_graph=True backward on Intel XPU without weight mutation.

## Why microbatch 16 is not frozen as the final training value

No tested candidate failed, so B2S did not find the operational ceiling. The candidate-16 timing projected through the frozen 11,520-profile training split and logical batch 8192 is operationally large for an 800-epoch run. That projection is diagnostic only, not a runtime promise.

## B2U

Benchmark 32, 64, 128, and 256 with the exact B2S graph. Each candidate must run in an isolated subprocess. OOM/device loss is an acceptable measurement outcome. No optimizer and no weight update are permitted.

After B2U, freeze the largest actually tested successful value and then decide whether a full COMP-XPU-005 execution contract is practical.

B3 remains blocked.
