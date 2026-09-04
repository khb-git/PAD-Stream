# V16E-1B2M-XPU — Conservative Residual Design Handoff

## Frozen conclusion

The Stage-2 conservative Godunov teacher and retained simple characteristic residual are objectively incompatible for positive Nc. B2L measured the teacher's own characteristic residual directly, and the positive-Nc values are far larger than those of either trained model.

## Do not launch another Stage-2 training experiment yet

The next scientific task is a coordinate derivation, not hyperparameter tuning.

Start from the physical conservative equation:

    dS/dtD + d[uD f_w(S)]/dxD = 0
    uD = exp(Nc*xD)

or expanded:

    dS/dtD + uD f_w'(S) dS/dxD + Nc uD f_w(S) = 0

The recurrent fan model uses:

    xi = xD / xD_star(tD)

so the time derivative at fixed physical xD is not generally the same as the time derivative at fixed xi. The next milestone must derive that chain rule and decide how xD_star(tD) is represented before any corrected conservative residual is coded.

## Branch preservation

* Preserve source-faithful Stage-2 lineage unchanged.
* Preserve COMP-XPU-004 checkpoint unchanged as the best current accuracy branch.
* Do not authorize B3 until a later explicit closure decision.
