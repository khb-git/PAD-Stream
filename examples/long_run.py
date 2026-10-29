"""Long-horizon 2D runs in yearly checkpoints (ROUTING_ABLATION section 14).

Runs one configuration year by year (12 x 30 d unless --steps_per_year), saving the
state, the transfer operator and per-year statistics after each year, so a run can
be resumed after a container restart.  Stops when --budget seconds are used.

    python examples/long_run.py --system argenta_brine --nx 6 --chem_substeps 6 --config da_ref --years 10
    python examples/long_run.py --system argenta_brine --nx 6 --chem_substeps 6 --config da_step --years 10 \
        --step_net models/argenta_brine_step_v1.npz --omega_tol cal
    python examples/long_run.py --compare long_argenta_brine_nx6_da_ref.pkl long_argenta_brine_nx6_da_step_cal.pkl
"""
import argparse, json, os, pickle, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_ablation as R

KIN = {"argenta_brine": ["Quartz", "K-feldspar", "Illite", "Kaolinite", "Chlorite(14A)"],
       "lower_mt_simon_brine": ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"],
       "upper_mt_simon_brine": ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite", "Chlorite(14A)", "Kaolinite"]}
KIN.update(lower_mt_simon_ibdp=KIN["lower_mt_simon_brine"], argenta_ibdp=KIN["argenta_brine"],
           upper_mt_simon_ibdp=KIN["upper_mt_simon_brine"])

ap = argparse.ArgumentParser()
ap.add_argument("--system", default="argenta_brine")
ap.add_argument("--nx", type=int, default=6)
ap.add_argument("--chem_substeps", type=int, default=6)
ap.add_argument("--config", default="da_ref")
ap.add_argument("--years", type=int, default=10)
ap.add_argument("--steps_per_year", type=int, default=12)
ap.add_argument("--step_net", default=None)
ap.add_argument("--step_kinetic", default=None)
ap.add_argument("--omega_tol", default="0.05")
ap.add_argument("--allow_precipitation", action="store_true",
                help="symmetric PK law for every mineral (no dissolution-only list)")
ap.add_argument("--budget", type=float, default=520.0, help="wall seconds before stopping (resume later)")
ap.add_argument("--compare", nargs=2, default=None, help="reference.pkl candidate.pkl: print error by year")
a = ap.parse_args()

if a.compare:
    ref, cand = (pickle.load(open(f, "rb")) for f in a.compare)
    R.select_system(ref["system"])
    st0 = ref["st0"]
    kin = np.array([p in KIN[ref["system"]] for p in R.PHASES])
    vm = np.array([m.molar_volume for m in st0.system.minerals])
    n0 = st0.mineral_moles()
    iC = R.ELEMENTS.index("C")
    print(f"{'year':>4} {'kin-vol err':>11} {'all-vol err':>11} {'dphi err':>9} {'dC err':>8} {'accepted':>9} "
          f"{'t_ref':>6} {'t_cand':>6}")
    for y in range(min(len(ref["years"]), len(cand["years"]))):
        r, c = ref["years"][y], cand["years"][y]
        dvt, dv = (r["n_min"] - n0) * vm, (c["n_min"] - n0) * vm
        ek = np.abs(dv - dvt)[:, kin].sum() / np.abs(dvt)[:, kin].sum()
        ea = np.abs(dv - dvt).sum() / np.abs(dvt).sum()
        dpt, dp = r["phi"] - st0.porosity, c["phi"] - st0.porosity
        ep = np.abs(dp - dpt).sum() / np.abs(dpt).sum()
        eC = np.abs(c["c_aq"][:, iC] - r["c_aq"][:, iC]).sum() / np.abs(r["c_aq"][:, iC]).sum()
        acc = c.get("kin_acc")
        acc = f"{acc:.1%}" if acc is not None else "-"
        print(f"{y + 1:4d} {ek:11.2%} {ea:11.2%} {ep:9.2%} {eC:8.1e} {acc:>9} {r['time']:6.0f} {c['time']:6.0f}")
    sys.exit()

R.select_system(a.system)
tag = a.config + ("" if a.config != "da_step" else "_" + a.omega_tol) + ("_precip" if a.allow_precipitation else "")
ck = f"long_{a.system}_nx{a.nx}_{tag}.pkl"
if a.config == "da_step":
    net = a.step_net
    if a.omega_tol == "cal":
        cal = json.load(open(net[:-4] + "_tol.json"))
        tol = np.array([float(cal.get(p, 0.05)) for p in R.PHASES])
    else:
        tol = float(a.omega_tol)
    R.STEP_MODEL.update(net=net, box=net[:-4] + "_box.npz", omega_tol=tol,
                        kinetic=a.step_kinetic.split(",") if a.step_kinetic else KIN[a.system])
if os.path.exists(ck):
    rec = pickle.load(open(ck, "rb"))
    phq = R.build(nx=a.nx, allow_precipitation=a.allow_precipitation)[0]
    c_in = rec["c_in"]
else:
    phq, st0, op0, c_in = R.build(nx=a.nx, allow_precipitation=a.allow_precipitation)
    rec = dict(system=a.system, st0=st0, c_in=c_in, state=st0, op=op0, years=[])
t_start = time.time()
dt = 30.0 * 86400.0 * 12 / a.steps_per_year
while len(rec["years"]) < a.years and time.time() - t_start < a.budget:
    y = len(rec["years"]) + 1
    r = R.run(a.config, phq, rec["state"], rec["op"], c_in, None, a.steps_per_year, dt,
              chem_substeps=a.chem_substeps)
    if r["failed"]:
        print(f"year {y}: FAILED {r['failed']}", flush=True)
        break
    st = r["state"]
    off = r.get("kinetic_offered") or 0
    rec["years"].append(dict(n_min=st.mineral_moles(), phi=st.porosity.copy(), c_aq=st.total_aq.copy(),
                             time=r["time"], mass_err=r["mass_err"],
                             kin_acc=(r["kinetic_accepted"] / off) if off else None, reasons=r["reasons"]))
    rec["state"], rec["op"] = st, r["op"]
    pickle.dump(rec, open(ck, "wb"))
    print(f"{tag} year {y}: {r['time']:.1f} s, mass err {r['mass_err']:.1e}"
          + (f", accepted {r['kinetic_accepted']}/{off}" if off else ""), flush=True)
print(f"{ck}: {len(rec['years'])}/{a.years} years done", flush=True)
