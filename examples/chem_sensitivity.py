"""Chemistry-assumption sensitivity with routed PHREEQC (ROUTING_ABLATION section 16).

Each variant is a routed-PHREEQC (da_ref) run; the script prints the carbon budget and
the mineral changes so variants can be compared with the default:

    python examples/chem_sensitivity.py --system argenta_brine --nx 6 --steps 4 --chem_substeps 6 \
        --variant default --variant precip --variant seed1e-5 --variant seed1e-7

variants: default; precip (symmetric PK law for every mineral, i.e. no dissolution-only list);
seed<x> (secondary-mineral seed volume fraction x).  A different brine is a different --system.
"""
import argparse, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_ablation as R

CARB_C = {"Calcite": 1, "Dolomite": 2, "Siderite": 1, "Magnesite": 1, "Ankerite": 2, "Dawsonite": 1}

ap = argparse.ArgumentParser()
ap.add_argument("--system", default="argenta_brine")
ap.add_argument("--nx", type=int, default=6)
ap.add_argument("--steps", type=int, default=4)
ap.add_argument("--dt_days", type=float, default=30.0)
ap.add_argument("--chem_substeps", type=int, default=6)
ap.add_argument("--variant", action="append", default=[])
a = ap.parse_args()
R.select_system(a.system)
for v in a.variant or ["default"]:
    kw = {}
    if v == "precip":
        kw["allow_precipitation"] = True
    elif v.startswith("seed"):
        kw["seed_vf"] = float(v[4:])
    phq, st0, op0, c_in = R.build(nx=a.nx, **kw)
    t = time.time()
    r = R.run("da_ref", phq, st0, op0, c_in, None, a.steps, a.dt_days * 86400.0, chem_substeps=a.chem_substeps)
    if r["failed"]:
        print(f"{a.system} {v}: FAILED at step {r['failed'][0]} ({time.time() - t:.0f} s): {r['failed'][1]}", flush=True)
        continue
    st = r["state"]
    dn = (st.mineral_moles() - st0.mineral_moles()).sum(0)
    iC = R.ELEMENTS.index("C")
    vb = lambda s: (s.porosity * s.brine_saturation * s.geom.cell_volume)
    dC_aq = float((st.total_aq[:, iC] * vb(st)).sum() - (st0.total_aq[:, iC] * vb(st0)).sum())
    dC_min = float(sum(dn[i] * CARB_C.get(p, 0) for i, p in enumerate(R.PHASES)))
    big = sorted(zip(R.PHASES, dn), key=lambda z: -abs(z[1]))[:4]
    print(f"{a.system} {v}: {time.time() - t:.0f} s | max|dphi| {np.abs(st.porosity - st0.porosity).max():.2e} | "
          f"dissolved C {dC_aq:+,.0f} mol | carbonate-mineral C {dC_min:+,.0f} mol | "
          + ", ".join(f"{p} {x:+,.0f}" for p, x in big) + f" | mass err {r['mass_err']:.0e}", flush=True)
