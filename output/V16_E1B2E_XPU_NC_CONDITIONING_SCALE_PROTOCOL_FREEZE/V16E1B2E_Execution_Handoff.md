# V16E-1B2E-XPU Execution Handoff

Authorized next experiment: **V16E-BLREP-COMP-XPU-003**.

One scientific change only: scale the copy of physical Nc presented to the neural-network conditioner by 1/0.30 so the training-grid conditioning interval maps from [0,0.30] to [0,1].

The physical Nc used by the Godunov teacher, breakthrough calculation, travel-time transform, physics residual, diagnostics, and labels must remain unscaled.

COMP-XPU-003 must start from fresh seed-1337 initialization and use 800 epochs with the exact frozen dataset and all COMP-XPU-002 settings otherwise unchanged.

B3 remains blocked until COMP-XPU-003 is compared with COMP-XPU-002.
