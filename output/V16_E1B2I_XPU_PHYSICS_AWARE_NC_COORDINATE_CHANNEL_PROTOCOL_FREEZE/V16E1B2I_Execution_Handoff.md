# V16E-1B2I-XPU Execution Handoff

Authorized next experiment: **V16E-BLREP-COMP-XPU-004**.

Use COMP-XPU-002 as the scientific baseline. Keep the exact raw physical 11-D conditioner unchanged and add one runtime-derived sequence channel:

    eta = y(xi*xD_star; Nc) / y(xD_star; Nc)

where y(x;Nc) = -expm1(-Nc*x)/Nc with the exact Nc->0 limit y=x.

The sequence feature array becomes [xi, eta]. The Godunov teacher, physical Nc, physics residual, loss weights, training schedule, dataset, and all other settings remain unchanged.

COMP-XPU-003 scaling is not carried forward into COMP-XPU-004.

B3 remains blocked until COMP-XPU-004 is trained and compared against COMP-XPU-002 using the frozen diagnostics.
