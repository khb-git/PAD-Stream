"""Coupled test of the step surrogate's overshoot tolerance (ROUTING_ABLATION section 13).

For one coupled case: routed PHREEQC is the reference (cached), and da_step is run for
each network and each tolerance.  A tolerance is a number (all minerals), ``inf`` (no
overshoot repair or check), or ``cal`` (per-mineral, the 95th percentile of the
network's held-out |SI_end| error, overshoot_tolerance_calibration.py);
``check:repair`` sets the two separately (``cal:inf`` = calibrated check, no repair).
The reference run also reports how many of its own kinetic solves the sign-flip check
would reject.

    python examples/overshoot_tolerance_sweep.py --system argenta_brine --nx 6 --steps 4 --dt_days 30 \
        --chem_substeps 6 --nets models/argenta_brine_step_v1.npz --tols 0.05,0.2,inf,cal
"""
import argparse, json, os, pickle, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput

KIN = {"argenta_brine": ["Quartz", "K-feldspar", "Illite", "Kaolinite", "Chlorite(14A)"],
       "lower_mt_simon_brine": ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"],
       "upper_mt_simon_brine": ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite", "Chlorite(14A)", "Kaolinite"]}
KIN.update(lower_mt_simon_ibdp=KIN["lower_mt_simon_brine"], argenta_ibdp=KIN["argenta_brine"],
           upper_mt_simon_ibdp=KIN["upper_mt_simon_brine"])


def cal_tol(net):
    """Per-mineral tolerance stored next to the network (<net>_tol.json)."""
    return {k: v for k, v in json.load(open(net[:-4] + "_tol.json")).items() if not k.startswith("_")}


ap = argparse.ArgumentParser()
ap.add_argument("--system", default="argenta_brine")
ap.add_argument("--nx", type=int, default=6)
ap.add_argument("--steps", type=int, default=4)
ap.add_argument("--dt_days", type=float, default=30.0)
ap.add_argument("--chem_substeps", type=int, default=6)
ap.add_argument("--nets", required=True, help="comma list of step networks (.npz; box = <name>_box.npz)")
ap.add_argument("--tols", default="0.05,0.2,0.5,1,inf,cal")
ap.add_argument("--cache", default="tolsweep")
ap.add_argument("--ref_undersat", default="",
                help="comma list: cells where one of these minerals is undersaturated go to PHREEQC (section 17)")
ap.add_argument("--dissolution_constraint", action="store_true",
                help="zero the extent of dissolution-only minerals that stay supersaturated (section 17)")
a = ap.parse_args()
R.select_system(a.system)
kin = KIN[a.system]
phq, st0, op0, c_in = R.build(nx=a.nx)
dt = a.dt_days * 86400.0
case = f"{a.system}_nx{a.nx}_s{a.steps}_dt{a.dt_days:g}_cs{a.chem_substeps}"
cache = f"{a.cache}_ref_{case}.pkl"
if os.path.exists(cache):
    ref, self_check = pickle.load(open(cache, "rb"))
else:
    # wrap the reference's kinetic solves to see how often the sign-flip check rejects PHREEQC itself
    counts = {"cells": 0, **{t: 0 for t in (0.05, 0.2, 0.5, 1.0)}}
    orig = phq.kinetic
    kin_idx = [R.PHASES.index(m) for m in kin]

    def kinetic(x: ChemInput):
        xi = orig(x)
        si0 = phq.speciate(x)[1]
        si1 = phq.speciate(ChemInput(np.clip(x.n_aq + xi @ phq.nu, 0, None), np.clip(x.n_min - xi, 0, None),
                                     x.v_brine, x.v_bulk, x.area, x.T, x.P, 0.0))[1]
        valid = (si0 > -50) & (si1 > -50)
        counts["cells"] += len(xi)
        for t in (0.05, 0.2, 0.5, 1.0):
            flip = (np.sign(si0) * si1 < -t) & (np.abs(xi) > 0) & valid
            counts[t] += int(flip[:, kin_idx].any(1).sum())
        return xi
    phq.kinetic = kinetic
    ref = R.run("da_ref", phq, st0, op0, c_in, None, a.steps, dt, chem_substeps=a.chem_substeps)
    phq.kinetic = orig
    ref["time"] = None                      # inflated by the extra speciation
    self_check = counts
    pickle.dump((ref, self_check), open(cache, "wb"))
n = self_check["cells"]
print(f"{case}: reference kinetic solves {n}; rejected by the sign-flip check at tol "
      + ", ".join(f"{t:g}: {self_check[t] / n:.1%}" for t in (0.05, 0.2, 0.5, 1.0)), flush=True)

kmask = np.array([p in kin for p in R.PHASES])
vm = np.array([m.molar_volume for m in st0.system.minerals])
n0 = st0.mineral_moles()
dvt = (ref["state"].mineral_moles() - n0) * vm
for net in a.nets.split(","):
    name = os.path.basename(net)[:-4]
    for tol in a.tols.split(","):
        # "<check>" or "<check>:<repair>"; the repair tolerance defaults to the check's
        parse = lambda v: (np.array([cal_tol(net).get(p, 0.05) for p in R.PHASES]) if v == "cal" else float(v))
        chk, rep = (tol.split(":") + [None])[:2]
        R.STEP_MODEL.update(net=net, box=net[:-4] + "_box.npz", kinetic=kin, omega_tol=parse(chk),
                            dissolution_constraint=a.dissolution_constraint,
                            ref_undersat=[m for m in a.ref_undersat.split(",") if m])
        R.STEP_MODEL.pop("repair_tol", None)
        if rep is not None:
            R.STEP_MODEL["repair_tol"] = parse(rep)
        r = R.run("da_step", phq, st0, op0, c_in, None, a.steps, dt, chem_substeps=a.chem_substeps)
        if r["failed"]:
            print(f"{name} tol {tol}: FAILED {r['failed']}", flush=True); continue
        c = R.compare(r, ref, st0)
        dv = (r["state"].mineral_moles() - n0) * vm
        ek = np.abs(dv - dvt)[:, kmask].sum() / np.abs(dvt)[:, kmask].sum()
        per = {p: round(float(e), 3) for p, e in zip(R.PHASES, c["mineral_rel_L1"]) if p in kin}
        print(f"{name + ('+dc' if a.dissolution_constraint else '') + ('+ru' if a.ref_undersat else ''):30s} tol {tol:9s} accepted {r['kinetic_accepted']:5d}/{r['kinetic_offered']:<5d} "
              f"({r['kinetic_accepted'] / r['kinetic_offered']:5.1%})  kin-vol err {ek:6.2%}  "
              f"dphi err {c['dphi_rel_L1']:.2e}  dC err {c['dC_rel_L1']:.1e}  time {r['time']:5.1f} s  "
              f"rejected {r['reasons']}  per-mineral {per}", flush=True)
