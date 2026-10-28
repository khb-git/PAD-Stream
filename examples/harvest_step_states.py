"""Harvest the kinetic cell states the step surrogate could not take.

Runs ``da_step`` on a coupled case that is NOT the test case (different grid
and time step; the permeability seed does not change these runs, because the
synthetic streamlines ignore permeability) and saves every kinetic cell that was
rejected by the overshoot check or routed outside the training box, with its
PHREEQC extents.  These states seed focused training samples
(generate_step_data_focused.py), in the spirit of the on-demand training of
Leal et al. (2020) but done offline so the test run stays unseen.

    python examples/harvest_step_states.py --system argenta_brine --nx 5 \
        --steps 5 --dt_days 20 --chem_substeps 6 --step_net NET --step_box BOX \
        --step_kinetic Quartz,K-feldspar,Illite,Kaolinite,Chlorite(14A) --out harvest.npz
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_ablation as R

ap = argparse.ArgumentParser()
ap.add_argument("--system", default="argenta_brine")
ap.add_argument("--seed", type=int, default=11)
ap.add_argument("--nx", type=int, default=5)
ap.add_argument("--steps", type=int, default=5)
ap.add_argument("--dt_days", type=float, default=20.0)
ap.add_argument("--chem_substeps", type=int, default=6)
ap.add_argument("--step_net", required=True)
ap.add_argument("--step_box", required=True)
ap.add_argument("--step_kinetic", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
assert (a.nx, a.dt_days) not in ((6, 30.0), (7, 25.0)), "that is a test case (ROUTING_ABLATION section 12)"
R.select_system(a.system)
R.STEP_MODEL.update(net=a.step_net, box=a.step_box, kinetic=a.step_kinetic.split(","), harvest=True)
phq, st0, op0, c_in = R.build(seed=a.seed, nx=a.nx)
res = R.run("da_step", phq, st0, op0, c_in, None, a.steps, a.dt_days * 86400.0, chem_substeps=a.chem_substeps)
keep = [(x, xi) for mode, x, xi in res["buffer"] if mode == "kinetic"]
cat = lambda f: np.concatenate([f(x, xi) for x, xi in keep])
dt = cat(lambda x, xi: np.broadcast_to(np.asarray(x.dt, float), (len(x.v_brine),)))
np.savez(a.out, n_aq=cat(lambda x, xi: x.n_aq), n_min=cat(lambda x, xi: x.n_min), vb=cat(lambda x, xi: x.v_brine),
         area=cat(lambda x, xi: x.area), T=cat(lambda x, xi: np.broadcast_to(x.T, (len(x.v_brine),))),
         P=cat(lambda x, xi: np.broadcast_to(x.P, (len(x.v_brine),))), dt=dt,
         act=cat(lambda x, xi: x.mask()), xi=cat(lambda x, xi: xi), V=st0.geom.cell_volume)
print(f"harvested {len(dt)} kinetic cell states (rejected {res['reasons']}, routed {res['routed']}) -> {a.out}")
