"""Timing and conservation check at PAD-Stream production size.

15 x 50 x 50 grid (20 x 20 x 4 ft), 1078 streamlines x 200 CVs, as in V15-SG6.
Streamlines here are synthetic quarter-five-spot arcs (no SG5 artifact needed);
point ``--sg6`` at a real PAD_Stream_V15SG6 transport database to use it.

Chemistry is calcite + dolomite in a {Ca, Mg, C, H+} total basis with
illustrative parameters (see the kinetic parameter table for sourced values),
so that the router produces a mix of EQUILIBRIUM, KINETIC and SKIP cells.
"""

import argparse
import time

import numpy as np

from padstream_rt import (ChemicalSystem, GridGeometry, Mineral, ReactiveState,
                          ReferenceBackend, RoutingConfig, StreamlineBundle,
                          SurrogateBackend, TransferOperator, reactive_step)
from padstream_rt.state import MD_TO_M2


def synthetic_bundle(geom, nsl=1078, nnode=201, phi=0.2, total_q=714.29 / 86400):
    rng = np.random.default_rng(7)
    Lx, Ly, Lz = geom.nx * geom.dx, geom.ny * geom.dy, geom.nz * geom.dz
    s = np.linspace(0, 1, nnode)
    xyz, tau = [], []
    q = np.full(nsl, total_q / nsl)
    for i in range(nsl):
        a = rng.uniform(0.05, 0.95)
        z = rng.uniform(0.02, 0.98) * Lz
        x = s * Lx
        y = np.clip(a * Ly + 0.15 * Ly * np.sin(np.pi * s) * (1 - 2 * a), 0, Ly * 0.9999)
        pts = np.stack([np.clip(x, 0, Lx * 0.9999), y, np.full(nnode, z)], 1)
        ds = np.r_[0, np.linalg.norm(np.diff(pts, axis=0), axis=1)]
        tau.append(np.cumsum(ds) * phi * 50.0)   # arbitrary positive TOF; PV* rescales it
        xyz.append(pts)
    return StreamlineBundle(np.array(xyz), np.array(tau), q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sg6", default=None)
    ap.add_argument("--steps", type=int, default=5)
    args = ap.parse_args()
    geom = GridGeometry()
    n = geom.ncell
    calcite = Mineral("calcite", [1, 0, 1, -1], 36.934e-6, 1.85, -5.81, 23.5e3,
                      -0.30, 14.4e3, 1.0, specific_area=1e4)
    dolomite = Mineral("dolomite", [1, 1, 2, -2], 64.365e-6, 2.5, -7.53, 52.2e3,
                       -3.19, 36.1e3, 0.5, specific_area=1e3)
    sysm = ChemicalSystem(["Ca", "Mg", "C", "H+"], [calcite, dolomite],
                          c_eq_scale=np.array([5.0, 5.0]))
    rng = np.random.default_rng(1)
    st = ReactiveState(geom, sysm, porosity=0.2,
                       perm=np.repeat(rng.lognormal(np.log(100), 1, n)[:, None], 3, 1) * MD_TO_M2,
                       brine_saturation=rng.uniform(0.3, 1.0, n),
                       total_aq=np.tile([1.0, 0.5, 1.0, 1e-2], (n, 1)),
                       mineral_vf=np.column_stack([rng.uniform(0, 0.03, n), rng.uniform(0, 0.05, n)]),
                       temperature=320.0, pressure=15e6)
    bundle = StreamlineBundle.from_sg6(args.sg6) if args.sg6 else synthetic_bundle(geom)
    t0 = time.perf_counter()
    op = TransferOperator(geom, bundle, st.porosity * geom.cell_volume)
    print(f"operator build: {time.perf_counter() - t0:.2f} s, visited cells "
          f"{op.visited.sum()}/{n}, CVs {op.pv.size}")
    ref = ReferenceBackend(sysm)
    sur = SurrogateBackend(lambda x, mode: {"xi": getattr(ref, mode)(x)}, ref)
    fb = st.brine_saturation ** 2 / (st.brine_saturation ** 2 + 0.1 * (1 - st.brine_saturation) ** 2)
    for k in range(args.steps):
        t0 = time.perf_counter()
        rep = reactive_step(st, op, sur, 5 * 86400.0, fb, c_inlet=np.array([1.0, 0.5, 20.0, 5.0]),
                            routing=RoutingConfig(da_eq=10.0, da_skip=1e-4))
        print(f"step {k}: {time.perf_counter() - t0:.2f} s  {rep.regime_counts}  "
              f"max |mass err| {np.abs(rep.mass_balance_error).max():.1e}  "
              f"substeps {rep.transport_substeps}  max dk/k {rep.max_rel_dk:.2e}\n    per mineral: {rep.extra['per_mineral']}")


if __name__ == "__main__":
    main()
