# V16E-1B2N-XPU — Conservative Residual Implementation Handoff

## Exact residual to implement

For network N(xi,tD,X,...), X=xD_star(tD):

    R_cons = N_tD + Xdot*N_X
             - (xi*Xdot/X)*N_xi
             + (1/X) d/dxi [ exp(Nc*xi*X) fw(N) ]

Equivalent expanded form:

    R_cons = N_tD + Xdot*N_X
             + [exp(Nc*xi*X) fw'(N)/X - xi*Xdot/X] N_xi
             + Nc exp(Nc*xi*X) fw(N)

## Front speed

Physical Rankine-Hugoniot closure:

    Xdot = exp(Nc*X) sigma_BL
    sigma_BL = [fw(Sw_star)-fw(swc)]/(Sw_star-swc)

The B2N audit quantifies how this closure compares with finite-difference speeds of the frozen finite-resolution Godunov mid-jump fronts.

## Critical autograd requirement

Because tD and xD_star are separate network conditioner entries, N_tD alone is NOT the physical derivative at fixed xi. The term Xdot*N_X is mandatory.

## Next milestone

Do not train yet. First implement a residual-only verification harness that compares conservative-form and expanded-form autograd residuals, checks Nc=0 nesting, checks finite values/bounds, and evaluates the new residual on the frozen Godunov teacher before any optimizer is created.
