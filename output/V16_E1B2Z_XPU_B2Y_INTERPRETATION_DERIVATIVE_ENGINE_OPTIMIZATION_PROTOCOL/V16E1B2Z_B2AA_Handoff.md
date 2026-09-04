# V16E-1B2Z-XPU — B2AA Batched-VJP Optimization Handoff

## B2Y certified result

The warmed exact corrected graph remains substantially more expensive than the matched first-order control. Forward and residual algebra are negligible relative to local recurrent derivative construction and backward through the create_graph=True derivative graph.

## First optimization branch

Do not change the model or physics. Replace only the 64-call Python loop used to obtain N_xi, N_tD, and N_X with one batched VJP call using `torch.autograd.grad(..., is_grads_batched=True)` and 64 one-hot sequence-output cotangents.

## Equivalence is mandatory

Before timing is considered useful, compare loop vs batched engines for:

* N_xi
* N_tD
* N_X
* corrected residual
* physics loss
* complete total loss
* every parameter gradient after backward

Only a float32-machine-epsilon-derived implementation budget may be used.

## Performance

For both engines: one warm-up plus three measured repeats on the exact same frozen 128 rows.

No optimizer. No weight update. If Intel XPU/LSTM does not support the batched-VJP path, preserve the exact error and stop rather than changing the scientific graph.

COMP-XPU-005 full training and B3 remain blocked.
