"""Calibrate the overshoot tolerance of the step surrogate on held-out samples.

For each held-out PHREEQC KINETICS sample (the same split the network was
trained with) this compares the saturation index at the END of the step for
the predicted and the reference extents:

* how often the REFERENCE step itself would fail the sign-flip check
  (sign(SI_0) * SI_end < -tol) or a direction check (a mineral's own extent
  carries it past equilibrium): a check the reference fails is rejecting
  physics, not network error;
* |SI_end(pred) - SI_end(ref)| per mineral: the network's error expressed in
  the units of the check.  Its 95th percentile is the error-matched tolerance.

    python examples/overshoot_tolerance_calibration.py argenta_brine models/argenta_brine_step_v1.npz \
        arg_chunk1.npz ... arg_chunk6.npz [--focus focus_chunk1.npz ...]
"""
import argparse, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput
from padstream_rt.surrogate import MLP, step_features, positivity_limit, STEP_Y_SCALE

KIN = {"argenta_brine": ["Quartz", "K-feldspar", "Illite", "Kaolinite", "Chlorite(14A)"],
       "lower_mt_simon_brine": ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"]}
ap = argparse.ArgumentParser()
ap.add_argument("system")
ap.add_argument("net")
ap.add_argument("data", nargs="+")
ap.add_argument("--focus", nargs="*", default=[])
ap.add_argument("--tols", default="0.05,0.1,0.2,0.3,0.5,1.0")
a = ap.parse_args()
R.select_system(a.system)
phq = R.build(nx=2)[0]
kin = KIN[a.system]; kin_idx = [R.PHASES.index(m) for m in kin]
d = [np.load(f) for f in a.data + a.focus]
src = np.concatenate([np.full(len(x["vb"]), int(j >= len(a.data))) for j, x in enumerate(d)])
cat = lambda k: np.concatenate([x[k] for x in d])
ok = cat("ok"); V = float(d[0]["V"])
n_aq, n_min, vb, area, T, P, dt, xi_all = (cat(k)[ok] for k in ("n_aq", "n_min", "vb", "area", "T", "P", "dt", "xi"))
src = src[ok]
# reproduce the training split (train_step_surrogate*.py: seed-0 permutation, first nt held out)
nt = 3000 + 1000 * bool(a.focus)
te = np.random.default_rng(0).permutation(len(vb))[:nt]
n_aq, n_min, vb, area, T, P, dt, xi_t, src = (z[te] for z in (n_aq, n_min, vb, area, T, P, dt, xi_all, src))
x0 = ChemInput(n_aq, n_min, vb, V, area, T, P, 0.0)
pH, si0 = phq.speciate(x0)
F = np.column_stack([step_features(n_aq, n_min, vb, area, T, P, dt, V, R.ELEMENTS, kin_idx), pH,
                     np.clip(si0[:, kin_idx], -30, 10)])
net = MLP.load(a.net)
kgw = vb * 1000.0
xi_p = np.zeros_like(n_min)
xi_p[:, kin_idx] = np.sinh(net.predict(F)) * STEP_Y_SCALE * kgw[:, None]
act = np.zeros_like(n_min, bool); act[:, kin_idx] = True
xi_p = positivity_limit(np.where(act, xi_p, 0.0), n_aq, n_min, phq.nu)
xi_t = np.where(act, xi_t, 0.0)


def si_end(xi):
    return phq.speciate(ChemInput(np.clip(n_aq + xi @ phq.nu, 0, None), np.clip(n_min - xi, 0, None),
                                  vb, V, area, T, P, 0.0))[1]


s_t, s_p = si_end(xi_t), si_end(xi_p)


def check(si_0, si_1, xi, tol, kind):
    """Cells x kinetic minerals flagged.  "flip": the SurrogateBackend check (SI changes
    sign by more than tol).  "dir": a mineral's own extent overshoots its equilibrium -
    it dissolved (xi > 0) yet ends supersaturated, or precipitated (xi < 0) yet ends
    undersaturated, by more than tol.  SI = -999 (an element absent) never counts."""
    valid = (si_0 > -50) & (si_1 > -50)
    if kind == "flip":
        bad = (np.sign(si_0) * si_1 < -tol) & (np.abs(xi) > 0)
    else:
        bad = ((xi > 0) & (si_1 > tol)) | ((xi < 0) & (si_1 < -tol))
    return (bad & valid)[:, kin_idx]
print(f"{a.system}  {os.path.basename(a.net)}  held-out n={nt}" + (f" (focused {src.sum()})" if a.focus else ""))
tols = [float(t) for t in a.tols.split(",")]
for name, sel in (("all", np.ones(nt, bool)),) + ((("broad", src == 0), ("focused", src == 1)) if a.focus else ()):
    print(f"-- {name} samples (n={sel.sum()})")
    print("   cells failing:     sign-flip check (current)     direction check")
    print("                       reference   network          reference   network")
    for tol in tols:
        fr = [check(si0, s, xi, tol, kind)[sel].any(1).mean() for kind in ("flip", "dir") for s, xi in ((s_t, xi_t), (s_p, xi_p))]
        print(f"   tol {tol:<5g}          {fr[0]:6.1%}     {fr[1]:6.1%}           {fr[2]:6.1%}     {fr[3]:6.1%}")
    print("   |SI_end(net) - SI_end(ref)| percentiles 50/90/95/99, minerals that react:")
    pooled = []
    for j, m in zip(kin_idx, kin):
        r = sel & (np.abs(xi_t[:, j]) > 0) & (np.minimum(s_t[:, j], s_p[:, j]) > -50) & (si0[:, j] > -50)
        e = np.abs(s_p[r, j] - s_t[r, j]); pooled.append(e)
        print(f"     {m:14s} n={r.sum():5d}  " + " / ".join(f"{q:.3f}" for q in np.percentile(e, [50, 90, 95, 99])))
    e = np.concatenate(pooled)
    print(f"     {'pooled':14s} n={len(e):5d}  " + " / ".join(f"{q:.3f}" for q in np.percentile(e, [50, 90, 95, 99])))
