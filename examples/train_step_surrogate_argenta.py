"""Train the Argenta step surrogate.

Same features and targets as train_step_surrogate.py.

* v1 (examples/models/argenta_brine_step_v1.npz): arg_chunk1-6 only.  Held-out
  relative L1 error 4.4-8.8 % per mineral (a 3x256 net, 500 epochs, was no better).
* v2 (argenta_brine_step_v2.npz): plus the focused near-equilibrium samples
  (focus_chunk1-4.npz, generate_step_data_focused.py; 13,140 samples).  Held-out
  error: broad 6-18 %, focused 3-38 % per mineral.  Mixed coupled results
  (docs/ROUTING_ABLATION_2026-10-27.md section 12); v1 stays the default.

    python examples/train_step_surrogate_argenta.py 350 [focus_chunk1.npz ...]
"""
import sys, time, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput
from padstream_rt.surrogate import step_features, fit_mlp, STEP_Y_SCALE
R.select_system("argenta_brine")
phq = R.build(nx=2)[0]
KIN = ["Quartz", "K-feldspar", "Illite", "Kaolinite", "Chlorite(14A)"]
kin_idx = [R.PHASES.index(m) for m in KIN]
extra = sys.argv[2:]
d = [np.load(f"arg_chunk{i}.npz") for i in range(1, 7)] + [np.load(f) for f in extra]
src = np.concatenate([np.full(len(x["vb"]), int(j >= 6)) for j, x in enumerate(d)])   # 1 = focused
cat = lambda k: np.concatenate([x[k] for x in d])
ok = cat("ok"); V = float(d[0]["V"])
n_aq, n_min, vb, area, T, P, dt = (cat(k)[ok] for k in ("n_aq", "n_min", "vb", "area", "T", "P", "dt"))
src = src[ok]
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
rng = np.random.default_rng(0); idx = rng.permutation(len(F)); nt = 3000 + 1000 * bool(extra)
te, tr = idx[:nt], idx[nt:]
t = time.time()
m, h = fit_mlp(F[tr], Y[tr], hidden=(160, 160, 160), epochs=int(sys.argv[1]) if len(sys.argv) > 1 else 400, verbose=True)
print("train", round(time.time() - t), "s", flush=True)
tag = "_v2" if extra else ""
m.save(f"arg_step_net{tag}.npz"); np.savez(f"arg_step_box{tag}.npz", x_min=F[tr].min(0), x_max=F[tr].max(0))
for name, sel in (("broad", src[te] == 0), ("focused", src[te] == 1)):
    if sel.any():
        P_ = m.predict(F[te][sel]); xi_p = np.sinh(P_) * STEP_Y_SCALE; xi_t = np.sinh(Y[te][sel]) * STEP_Y_SCALE
        print(f"held-out relative L1 error ({name}, n={sel.sum()})",
              dict(zip(KIN, (np.abs(xi_p - xi_t).sum(0) / np.abs(xi_t).sum(0)).round(4))))
