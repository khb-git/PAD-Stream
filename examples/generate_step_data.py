"""PHREEQC KINETICS step samples for the step-map surrogate (lower Mt. Simon brine).

Each sample: a mixture of formation and CO2-saturated injected brine (Liu et al.
2011 brine, conservative ions +-25 %, carbon over a wide range), partly
pre-reacted with the primary silicates, random porosity / saturation / mineral
amounts / reactive areas (factor 0.3-3) / T 45-60 C / P 120-180 bar / dt 5-60 d;
label: the mineral extents of one PHREEQC KINETICS (CVODE) step.  Writes
step2_chunk<id>.npz.  Runs stop after ~8 min so they fit short sessions; the
27 Oct 2026 pilot used chunks 1-4 (35,200 samples, ~27 ms each).

    python examples/generate_step_data.py <chunk_id> <n_samples>
"""
import sys, time, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput
from padstream_rt.damkohler import reactive_area
R.select_system("lower_mt_simon_brine")
phq, st, op, c_in = R.build(nx=2)
KIN = ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"]
kin = np.array([p in KIN for p in R.PHASES])
form = st.total_aq[0].copy()
nu = phq.nu
chunk, N = int(sys.argv[1]), int(sys.argv[2])
rng = np.random.default_rng(1000 + chunk)
V = st.geom.cell_volume
vf0 = st.mineral_vf[0]; vm = np.array([m.molar_volume for m in phq.minerals])
spec = np.array([m.specific_area for m in phq.minerals])
f = rng.uniform(0, 1, N) ** 0.7                      # mixing fraction of injected brine
phi = rng.uniform(0.15, 0.25, N); sb = rng.uniform(0.3, 1.0, N)
vb = phi * sb * V; kgw = vb * 1000.0
c = (1 - f)[:, None] * form[None, :] + f[:, None] * c_in[None, :]       # mol/m3 brine
# brine variability: conservative ions +-25 % (log10 +-0.1), carbon over a wide
# range (calcite precipitation at equilibrium consumes it; CO2 adds it)
E_ = R.ELEMENTS
for e in ("Na", "K", "Mg", "Ca", "Cl", "S"):
    c[:, E_.index(e)] *= 10 ** rng.uniform(-0.1, 0.1, N)
iC = E_.index("C")
c[:, iC] = np.clip(c[:, iC] * 10 ** rng.uniform(-1.5, 0.15, N), 1e-3, None)
n_aq = c * vb[:, None]
# prior partial dissolution of the primaries (products already in solution)
pre = np.where(rng.random((N, len(R.PHASES))) < 0.7, 10 ** rng.uniform(-6, -2.5, (N, len(R.PHASES))), 0.0) * kin
n_aq = n_aq + (pre * kgw[:, None]) @ nu
n_min = (vf0 * V / vm)[None, :] * rng.uniform(0.7, 1.3, (N, len(R.PHASES)))
area = (vf0 * spec)[None, :] * 10 ** rng.uniform(-0.5, 0.5, (N, len(R.PHASES)))
T = rng.uniform(318.15, 333.15, N); P = rng.uniform(120e5, 180e5, N)
dt = 86400.0 * 10 ** rng.uniform(np.log10(5), np.log10(60), N)
act = np.tile(kin, (N, 1))
XI = np.zeros((N, len(R.PHASES))); ok = np.ones(N, bool)
t0 = time.time()
B = 200
for s0 in range(0, N, B):
    sl = slice(s0, s0 + B)
    x = ChemInput(n_aq[sl], n_min[sl], vb[sl], V, area[sl], T[sl], P[sl], dt[sl], act[sl])
    try:
        XI[sl] = phq.kinetic(x)
    except RuntimeError:          # retry row by row to isolate failures
        for i in range(s0, min(s0 + B, N)):
            try:
                XI[i] = phq.kinetic(ChemInput(n_aq[[i]], n_min[[i]], vb[[i]], V, area[[i]], T[[i]], P[[i]], dt[[i]], act[[i]]))[0]
            except RuntimeError:
                ok[i] = False
    if time.time() - t0 > 470:
        N = min(s0 + B, N); break
np.savez(f"step2_chunk{chunk}.npz", n_aq=n_aq[:N], n_min=n_min[:N], vb=vb[:N], area=area[:N], T=T[:N], P=P[:N],
         dt=dt[:N], xi=XI[:N], ok=ok[:N], V=V)
print(f"chunk {chunk}: {N} samples, {ok[:N].sum()} ok, {time.time() - t0:.0f} s", flush=True)
