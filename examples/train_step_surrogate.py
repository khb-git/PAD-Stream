"""Train the step-map surrogate (examples/models/lower_mt_simon_brine_step_v1.npz).

Inputs: log10 molalities, charge feature, T, P, log10 dt, log10 reactive area and
mineral amount per kg water for the five kinetic minerals, plus PHREEQC pH and
their saturation indices.  Targets: asinh(extent per kg water / 1e-6).
3 x 160 tanh MLP, 350 epochs.  Held-out relative L1 error 2.7-4.4 % per mineral.

    python examples/train_step_surrogate.py 350     (run where the step*_chunk*.npz files are)
"""
import sys, time, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput
from padstream_rt.surrogate import step_features, fit_mlp, STEP_Y_SCALE
R.select_system("lower_mt_simon_brine")
phq = R.build(nx=2)[0]
KIN = ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"]
kin_idx = [R.PHASES.index(m) for m in KIN]
d = [np.load(f) for f in ("step_chunk1.npz", "step_chunk2.npz", "step2_chunk3.npz", "step2_chunk4.npz")]
cat = lambda k: np.concatenate([x[k] for x in d])
ok = cat("ok"); V = float(d[0]["V"])
n_aq, n_min, vb, area, T, P, dt = (cat(k)[ok] for k in ("n_aq", "n_min", "vb", "area", "T", "P", "dt"))
t = time.time()
pH, si = [], []
for s in range(0, len(vb), 2000):
    sl = slice(s, s + 2000)
    a, b = phq.speciate(ChemInput(n_aq[sl], n_min[sl], vb[sl], V, area[sl], T[sl], P[sl], 0.0))
    pH.append(a); si.append(b)
pH, si = np.concatenate(pH), np.concatenate(si)
print("speciation", round(time.time() - t, 1), "s for", len(vb), flush=True)
F = np.column_stack([step_features(n_aq, n_min, vb, area, T, P, dt, V, R.ELEMENTS, kin_idx), pH,
                     np.clip(si[:, kin_idx], -30, 10)])
kgw = vb * 1000.0
Y = np.arcsinh(cat("xi")[ok][:, kin_idx] / kgw[:, None] / STEP_Y_SCALE)
rng = np.random.default_rng(0); idx = rng.permutation(len(F)); nt = 3000
te, tr = idx[:nt], idx[nt:]
t = time.time()
m, h = fit_mlp(F[tr], Y[tr], hidden=(160, 160, 160), epochs=int(sys.argv[1]) if len(sys.argv) > 1 else 400, verbose=True)
print("train", round(time.time() - t), "s", flush=True)
m.save("step_net2.npz"); np.savez("step_box2.npz", x_min=F[tr].min(0), x_max=F[tr].max(0))
P_ = m.predict(F[te]); xi_p = np.sinh(P_) * STEP_Y_SCALE; xi_t = np.sinh(Y[te]) * STEP_Y_SCALE
print("held-out relative L1 error", dict(zip(KIN, (np.abs(xi_p - xi_t).sum(0) / np.abs(xi_t).sum(0)).round(4))))
