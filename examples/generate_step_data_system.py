"""PHREEQC KINETICS step samples for any brine system (step surrogate).

Generalises generate_step_data_argenta.py (same sampling) to a system named on the
command line; used for the Upper Mt. Simon test (ROUTING_ABLATION section 15).

    python examples/generate_step_data_system.py <system> <KIN,...> <EQ,...> <chunk_id> <n_samples>

Original Argenta notes follow.

As generate_step_data.py, for kinetic quartz, K-feldspar, illite, kaolinite and
chlorite, with dt 1-60 d and half the samples first equilibrated with calcite,
dolomite and anhydrite (as in the kinetic -> equilibrium substeps).  ~112 ms per
sample; the 27 Oct 2026 run used chunks 1-6 (23,800 samples).  Writes arg_chunk<id>.npz.

    python examples/generate_step_data_argenta.py <chunk_id> <n_samples>
"""
import sys, time, numpy as np
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import routing_ablation as R
from padstream_rt import ChemInput
from padstream_rt.damkohler import reactive_area
SYS, KIN_ARG, EQ_ARG = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0]] + sys.argv[4:]
R.select_system(SYS)
phq, st, op, c_in = R.build(nx=2)
KIN = KIN_ARG.split(",")
EQ = EQ_ARG.split(",")
kin = np.array([p in KIN for p in R.PHASES])
form = st.total_aq[0].copy()
nu = phq.nu
chunk, N = int(sys.argv[1]), int(sys.argv[2])
rng = np.random.default_rng(1000 + chunk + 7919 * (SYS != "argenta_brine"))
V = st.geom.cell_volume
vf0 = st.mineral_vf[0]; vm = np.array([m.molar_volume for m in phq.minerals])
spec = np.array([m.specific_area for m in phq.minerals])
f = rng.uniform(0, 1, N) ** 0.7                      # mixing fraction of injected brine
phi0 = float(st.porosity[0])                         # porosity range around the unit's own
phi = rng.uniform(max(0.04, phi0 - 0.06), phi0 + 0.06, N); sb = rng.uniform(0.3, 1.0, N)
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
_pending_eq = True
# prior partial dissolution of the primaries (products already in solution)
pre = np.where(rng.random((N, len(R.PHASES))) < 0.7, 10 ** rng.uniform(-6, -2.5, (N, len(R.PHASES))), 0.0) * kin
n_aq = n_aq + (pre * kgw[:, None]) @ nu
n_min = (vf0 * V / vm)[None, :] * rng.uniform(0.7, 1.3, (N, len(R.PHASES)))
area = (vf0 * spec)[None, :] * 10 ** rng.uniform(-0.5, 0.5, (N, len(R.PHASES)))
T = rng.uniform(318.15, 333.15, N); P = rng.uniform(120e5, 180e5, N)
dt = 86400.0 * 10 ** rng.uniform(np.log10(1), np.log10(60), N)
act = np.tile(kin, (N, 1))
# in the coupled run the kinetic call follows a carbonate re-equilibration
# (kinetic -> equilibrium substeps), so half the samples are first brought to
# equilibrium with calcite, dolomite and anhydrite
eqm = np.array([p in EQ for p in R.PHASES])
sel = rng.random(N) < 0.5
for s0 in range(0, N, 400):
    rows = np.flatnonzero(sel[s0:s0 + 400]) + s0
    if len(rows) == 0:
        continue
    xe = ChemInput(n_aq[rows], n_min[rows], vb[rows], V, area[rows], T[rows], P[rows], 0.0,
                   np.tile(eqm, (len(rows), 1)))
    try:
        dxi = phq.equilibrium(xe)
        n_aq[rows] = np.clip(n_aq[rows] + dxi @ nu, 0, None); n_min[rows] = np.clip(n_min[rows] - dxi, 0, None)
    except RuntimeError:
        pass
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
np.savez(f"{SYS}_chunk{chunk}.npz", n_aq=n_aq[:N], n_min=n_min[:N], vb=vb[:N], area=area[:N], T=T[:N], P=P[:N],
         dt=dt[:N], xi=XI[:N], ok=ok[:N], V=V)
print(f"chunk {chunk}: {N} samples, {ok[:N].sum()} ok, {time.time() - t0:.0f} s", flush=True)
