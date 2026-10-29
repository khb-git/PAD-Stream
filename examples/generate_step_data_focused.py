"""Focused PHREEQC KINETICS samples around harvested near-equilibrium states.

Each state from harvest_step_states.py (cells the step surrogate rejected in a
coupled run that is not the test case) is perturbed K times; Al and Si are
varied most (+-0.4 log units) so the samples straddle quartz / kaolinite
saturation, where the overshoot check rejects.  Writes focus_chunk<id>.npz in
the format of generate_step_data_argenta.py.

    python examples/generate_step_data_focused.py [--system <name>] <chunk_id> <K> harvest_a.npz [harvest_b.npz ...]
"""
import sys, time, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput

SYS = "argenta_brine"
if sys.argv[1] == "--system":                        # optional: --system <name> first
    SYS = sys.argv[2]; sys.argv = [sys.argv[0]] + sys.argv[3:]
R.select_system(SYS)
phq = R.build(nx=2)[0]
chunk, K, files = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3:]
H = [np.load(f) for f in files]
cat = lambda k: np.concatenate([h[k] for h in H])
V = float(H[0]["V"])
n_aq0, n_min0, vb0, area0, T0, P0, act0 = (cat(k) for k in ("n_aq", "n_min", "vb", "area", "T", "P", "act"))
rng = np.random.default_rng(5000 + chunk)
idx = np.repeat(np.arange(len(vb0)), K)
N = len(idx)
E = R.ELEMENTS
logspan = np.full(len(E), 0.05)                          # conservative ions
for e, s in (("Al", 0.4), ("Si", 0.4), ("K", 0.2), ("C", 0.2), ("Mg", 0.1), ("Ca", 0.1)):
    logspan[E.index(e)] = s
n_aq = n_aq0[idx] * 10 ** (rng.uniform(-1, 1, (N, len(E))) * logspan)
n_min = n_min0[idx] * rng.uniform(0.8, 1.2, (N, n_min0.shape[1]))
area = area0[idx] * 10 ** rng.uniform(-0.3, 0.3, (N, n_min0.shape[1]))
vb = vb0[idx] * rng.uniform(0.9, 1.1, N)
T = T0[idx] + rng.uniform(-2, 2, N); P = P0[idx] * rng.uniform(0.95, 1.05, N)
dt = 86400.0 * 10 ** rng.uniform(0, np.log10(15), N)
act = act0[idx]
XI = np.zeros_like(n_min); ok = np.ones(N, bool)
t0 = time.time(); B = 200
for s0 in range(0, N, B):
    sl = slice(s0, s0 + B)
    try:
        XI[sl] = phq.kinetic(ChemInput(n_aq[sl], n_min[sl], vb[sl], V, area[sl], T[sl], P[sl], dt[sl], act[sl]))
    except RuntimeError:
        for i in range(s0, min(s0 + B, N)):
            try:
                XI[i] = phq.kinetic(ChemInput(n_aq[[i]], n_min[[i]], vb[[i]], V, area[[i]], T[[i]], P[[i]], dt[[i]], act[[i]]))[0]
            except RuntimeError:
                ok[i] = False
    if time.time() - t0 > 470:
        N = min(s0 + B, N); break
np.savez(f"focus_chunk{chunk}.npz" if SYS == "argenta_brine" else f"{SYS}_focus_chunk{chunk}.npz", n_aq=n_aq[:N], n_min=n_min[:N], vb=vb[:N], area=area[:N], T=T[:N], P=P[:N],
         dt=dt[:N], xi=XI[:N], ok=ok[:N], V=V)
print(f"focus chunk {chunk}: {N} samples, {ok[:N].sum()} ok, {time.time() - t0:.0f} s", flush=True)
