"""Routing ablation on a lower Mt. Simon layer (claim 1 + claim 2 experiment).

One 50 x 50 x 1 layer of the PAD-Stream grid (20 x 20 x 4 ft cells), lower
Mt. Simon mineralogy from Freiburg et al. (2022) (mineralogy.py), PK 2004
kinetics, PHREEQC (phreeqc.dat) as the reference chemistry, CO2-saturated
2 m NaCl brine injected along synthetic quarter-five-spot streamlines.

Configurations (all use the same transport and the same time steps):

  truth        PHREEQC, every (cell, mineral) KINETIC            (reference)
  all_eq       PHREEQC, every (cell, mineral) EQUILIBRIUM        (common shortcut)
  da_ref       PHREEQC, a priori Damkohler routing               (claim 1 alone)
  aposteriori  surrogate everywhere + reference fallback         (Leal 2020-style)
  da_surr      Damkohler routing + surrogate + fallback          (claims 1 + 2)
  stiff_surr_S surrogate, but cells with stiffness ratio > S go to the
               PHREEQC reference a priori (SpeciationSurrogate.stiffness)
  da_sat_*     as da_*, with the saturation-aware Damkohler number
               (precipitating minerals limited by aqueous supply)

Reported per configuration: chemistry wall time, reference cell-solves,
fallback rate, max mass-balance error, and the error against ``truth`` of the
mineral changes, porosity change and dissolved carbon.

    python examples/routing_ablation.py --net examples/models/lower_mt_simon_speciation_v1.npz \
        --configs truth,all_eq,da_ref,aposteriori,stiff_surr_8 --steps 12
"""

from __future__ import annotations

import argparse
import os
import copy
import pickle
import time

import numpy as np

from padstream_rt import (ChemInput, GridGeometry, PhreeqcBackend, ReactiveState, RoutingConfig,
                          SurrogateBackend, TransferOperator, reactive_step)
from padstream_rt.kinetics import load_pk_parameters
from padstream_rt.mineralogy import DENSITY_G_CM3, c_eq_scales, unit_mineralogy
from padstream_rt.phreeqc_backend import ATM, _phreeqc
from padstream_rt.state import MD_TO_M2
from padstream_rt.surrogate import MLP, TRACE_MOLAL, SpeciationSurrogate

ELEMENTS = ["Na", "K", "Mg", "Fe", "Al", "Si", "C", "Cl"]
PHASES = ["Quartz", "K-feldspar", "Albite", "Siderite", "Illite", "Kaolinite"]
XRD = ["quartz", "k_feldspar", "plagioclase", "siderite", "illite_mica", None]
PK = ["quartz", "K-feldspar", "albite", "siderite (provisional; Sun et al. 2020 Table 4)",
      "illite (provisional; Sun et al. 2020 Table 4)", "kaolinite"]
MOLAR_MASS = dict(Quartz=60.08, **{"K-feldspar": 278.33}, Albite=262.22, Siderite=115.85,
                  Illite=389.34, Kaolinite=258.16)          # g/mol, phreeqc.dat formulae
DENS = dict(Quartz=DENSITY_G_CM3["quartz"], **{"K-feldspar": DENSITY_G_CM3["k_feldspar"]},
            Albite=DENSITY_G_CM3["plagioclase"], Siderite=DENSITY_G_CM3["siderite"],
            Illite=DENSITY_G_CM3["illite_mica"], Kaolinite=DENSITY_G_CM3["kaolinite"])
T_K, P_PA, NACL, LOG_PCO2_INJ = 323.15, 15e6, 2.0, 1.9


def brine_totals(log_pco2, phases_eq=()):
    """mol per m^3 brine of each element for 2 m NaCl at (T, P)."""
    p = _phreeqc("phreeqc.dat")
    eq = "\n".join([f" CO2(g) {log_pco2} 100"] + [f" {ph} 0 10" for ph in phases_eq])
    tr = "\n".join(f" {e} {TRACE_MOLAL}" for e in ("K", "Mg", "Fe(2)", "Al", "Si"))
    inp = (f"SELECTED_OUTPUT\n -reset false\nUSER_PUNCH\n -headings {' '.join(ELEMENTS)}\n"
           + "\n".join(f"{10 + i} PUNCH TOT(\"{e}\")" for i, e in enumerate(ELEMENTS))
           + f"\nSOLUTION 1\n temp {T_K - 273.15}\n pressure {P_PA / ATM}\n units mol/kgw\n pH 7 charge\n"
             f" Na {NACL}\n Cl {NACL}\n{tr}\nEQUILIBRIUM_PHASES 1\n{eq}\nEND")
    if p.RunString(inp):
        raise RuntimeError(p.GetErrorString())
    o = p.GetSelectedOutput()
    return np.array([float(o[e][-1]) for e in ELEMENTS]) * 1000.0


def synthetic_bundle(geom, nsl=400, nnode=201, total_q=714.29 / 86400 / 15, seed=7):
    from padstream_rt import StreamlineBundle
    rng = np.random.default_rng(seed)
    Lx, Ly = geom.nx * geom.dx, geom.ny * geom.dy
    s = np.linspace(0, 1, nnode)
    xyz, tau = [], []
    for _ in range(nsl):
        a = rng.uniform(0.02, 0.98)
        x = s * Lx
        y = np.clip(a * Ly + 0.15 * Ly * np.sin(np.pi * s) * (1 - 2 * a), 0, Ly * 0.9999)
        pts = np.stack([np.clip(x, 0, Lx * 0.9999), y, np.full(nnode, 0.5 * geom.dz)], 1)
        ds = np.r_[0, np.linalg.norm(np.diff(pts, axis=0), axis=1)]
        tau.append(np.cumsum(ds) * 10.0)
        xyz.append(pts)
    return StreamlineBundle(np.array(xyz), np.array(tau), np.full(nsl, total_q / nsl))


def build(roughness=1.0, seed=3, nx=25):
    um = unit_mineralogy("Lower Mt. Simon", roughness=roughness)
    vf, spec = {}, {}
    for ph, x in zip(PHASES, XRD):
        if x is None:
            vf[ph], spec[ph] = 1e-4, 6.0 / 1e-6 * roughness       # kaolinite seed (assumed)
        else:
            i = um.minerals.index(x)
            vf[ph], spec[ph] = um.vf_bulk[i], um.specific_area[i]
    kp = {ph: load_pk_parameters(n) for ph, n in zip(PHASES, PK)}
    vm = {ph: MOLAR_MASS[ph] / DENS[ph] * 1e-6 for ph in PHASES}
    phq = PhreeqcBackend(ELEMENTS, PHASES, kinetic_params=kp, specific_area=spec, molar_volume=vm)
    ceq = c_eq_scales(PHASES, T_K, P_PA, NACL, 10 ** LOG_PCO2_INJ)
    system = phq.chemical_system(ceq)
    geom = GridGeometry(nx=nx, ny=nx, nz=1)
    n = geom.ncell
    rng = np.random.default_rng(seed)
    st = ReactiveState(geom, system, porosity=um.porosity,
                       perm=np.repeat(rng.lognormal(np.log(110), 0.6, n)[:, None], 3, 1) * MD_TO_M2,
                       brine_saturation=0.6,
                       total_aq=np.tile(brine_totals(-1.0, ["Quartz", "Kaolinite", "K-feldspar"]), (n, 1)),
                       mineral_vf=np.tile([vf[p] for p in PHASES], (n, 1)),
                       temperature=T_K, pressure=P_PA)
    frac = nx * nx / 2500.0                     # same flux per unit area as the 50 x 50 layer
    op = TransferOperator(geom, synthetic_bundle(geom, nsl=max(int(400 * nx / 50), 50),
                                                 total_q=714.29 / 86400 / 15 * frac),
                          st.porosity * geom.cell_volume)
    return phq, st, op, brine_totals(LOG_PCO2_INJ)


def run(config, phq, st0, op0, c_in, net, steps, dt, da_eq=10.0, da_skip=1e-3):
    st, op = copy.deepcopy(st0), copy.deepcopy(op0)
    sb = st.brine_saturation
    fb = sb ** 2 / (sb ** 2 + 0.1 * (1 - sb) ** 2)
    stiff_max = float(config.split("_")[-1]) if config.startswith("stiff_surr_") else None
    surr = (SpeciationSurrogate(net, phq.minerals, ELEMENTS, stiff_max=stiff_max)
            if net is not None else None)
    T, P = st.temperature, st.pressure
    surrogate = config in ("aposteriori", "da_surr", "da_sat_surr") or stiff_max is not None
    if surrogate:
        backend = SurrogateBackend(surr, phq, speciate_fn=surr.speciate, keep_training_data=False)
        spec = lambda a, v: surr._spec(a, v, T, P)
    else:
        backend = phq
        spec = lambda a, v: phq.speciate(ChemInput(a, np.zeros((len(v), len(PHASES))), v, 1.0,
                                                   np.zeros((len(v), len(PHASES))), T, P, 0.0))
    pH_fn = lambda a, v: spec(a, v)[0]
    spec_fn = spec if config.startswith("da_sat") else None
    off = RoutingConfig(da_eq=np.inf, da_skip=0.0, buffer_cells=0)
    da = RoutingConfig(da_eq=da_eq, da_skip=da_skip, buffer_cells=1)
    routing = {"truth": off, "aposteriori": off,
               "all_eq": RoutingConfig(da_eq=0.0, da_skip=0.0, buffer_cells=0),
               "da_ref": da, "da_surr": da, "da_sat_ref": da, "da_sat_surr": da}.get(config, off)
    t_chem, mass_err, counts, ref_cells = 0.0, 0.0, [], 0
    failed = None
    for k in range(steps):
        t0 = time.perf_counter()
        try:
            rep = reactive_step(st, op, backend, dt, fb, c_inlet=c_in, routing=routing, pH_fn=pH_fn,
                                spec_fn=spec_fn)
        except RuntimeError as e:                       # PHREEQC did not converge
            failed = (k, str(e).strip().splitlines()[-1][:160])
            break
        t_chem += time.perf_counter() - t0
        mass_err = max(mass_err, float(np.abs(rep.mass_balance_error).max()))
        if backend is phq:                               # every routed cell is a PHREEQC solve
            ref_cells += int((st.regime != 0).any(axis=1).sum())
        counts.append(rep.extra["per_mineral"])
    stats = getattr(backend, "stats", None)
    if stats is not None:
        ref_cells = stats.rejected + stats.routed
    return dict(ref_cells=ref_cells, state=st, time=t_chem, mass_err=mass_err, per_mineral=counts, failed=failed,
                fallback=None if stats is None else stats.fallback_rate,
                routed=None if stats is None else stats.routed,
                reasons=None if stats is None else dict(stats.reasons),
                surr_cells=None if stats is None else stats.cells)


def compare(res, truth, st0):
    n0 = st0.mineral_moles()
    d_t = truth["state"].mineral_moles() - n0
    d = res["state"].mineral_moles() - n0
    scale = np.abs(d_t).sum(0)
    min_err = np.abs(d - d_t).sum(0) / np.maximum(scale, 1e-300)
    dphi_t = truth["state"].porosity - st0.porosity
    dphi = res["state"].porosity - st0.porosity
    iC = ELEMENTS.index("C")
    c_t, c = truth["state"].total_aq[:, iC], res["state"].total_aq[:, iC]
    vm = np.array([m.molar_volume for m in st0.system.minerals])
    dv_t, dv = d_t * vm, d * vm
    return dict(mineral_rel_L1=min_err,
                dvf_rel_L1=float(np.abs(dv - dv_t).sum() / max(np.abs(dv_t).sum(), 1e-300)),
                dphi_rel_L1=float(np.abs(dphi - dphi_t).sum() / max(np.abs(dphi_t).sum(), 1e-300)),
                dC_rel_L1=float(np.abs(c - c_t).sum() / np.abs(c_t).sum()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default=None)
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--dt_days", type=float, default=30.0)
    ap.add_argument("--roughness", type=float, default=1.0)
    ap.add_argument("--configs", default="truth,all_eq,da_ref,aposteriori,da_surr")
    ap.add_argument("--out", default=None)
    ap.add_argument("--nx", type=int, default=25)
    ap.add_argument("--cache", default="ablation_cache", help="prefix for cached truth / all_eq runs")
    ap.add_argument("--da_eq", type=float, default=10.0)
    ap.add_argument("--da_skip", type=float, default=1e-3)
    a = ap.parse_args()
    net = None
    if a.net:
        net = MLP.load(a.net) if a.net.endswith(".npz") else MLP.from_state(pickle.load(open(a.net, "rb")))
    phq, st0, op0, c_in = build(a.roughness, nx=a.nx)
    dt = a.dt_days * 86400.0
    results = {}
    for cfg in a.configs.split(","):
        cache = f"{a.cache}_{cfg}_nx{a.nx}_s{a.steps}_dt{a.dt_days:g}_r{a.roughness:g}.pkl" if a.cache else None
        if cfg in ("truth", "all_eq") and cache and os.path.exists(cache):
            results[cfg] = pickle.load(open(cache, "rb"))
        else:
            results[cfg] = run(cfg, phq, st0, op0, c_in, net, a.steps, dt, a.da_eq, a.da_skip)
            if cfg in ("truth", "all_eq") and cache:
                pickle.dump(results[cfg], open(cache, "wb"))
        r = results[cfg]
        if r["failed"]:
            print(f"{cfg:12s} FAILED at step {r['failed'][0]}: {r['failed'][1]}", flush=True)
            continue
        print(f"{cfg:12s} chem+transport {r['time']:7.1f} s  PHREEQC cell-solves {r['ref_cells']}  "
              f"(routed a priori {r.get('routed')})  max|mass err| {r['mass_err']:.1e}  "
              f"fallback {r['fallback']}  {r['reasons'] or ''}", flush=True)
    summary = {}
    for cfg, r in results.items():
        if cfg == "truth" or r["failed"]:
            summary[cfg] = dict(failed=r["failed"]) if r["failed"] else summary.get(cfg)
            continue
        c = compare(r, results["truth"], st0)
        summary[cfg] = dict(ref_cells=r["ref_cells"], time=r["time"], mass_err=r["mass_err"], fallback=r["fallback"],
                            reasons=r["reasons"], **c, last_regimes=r["per_mineral"][-1])
        print(f"{cfg:12s} d(mineral vol) err {c['dvf_rel_L1']:.2e}  dphi err {c['dphi_rel_L1']:.2e}  dC err {c['dC_rel_L1']:.2e}  "
              f"mineral err {dict(zip(PHASES, np.round(c['mineral_rel_L1'], 4)))}")
    summary["truth"] = dict(time=results["truth"]["time"], mass_err=results["truth"]["mass_err"],
                            last_regimes=results["truth"]["per_mineral"][-1],
                            dphi_max=float(np.abs(results["truth"]["state"].porosity - st0.porosity).max()))
    print("truth max |dphi|", summary["truth"]["dphi_max"])
    for cfg in ("da_ref", "da_surr", "da_sat_ref", "da_sat_surr"):
        if cfg in results:
            print(cfg, "final regimes", results[cfg]["per_mineral"][-1])
    if a.out:
        pickle.dump(summary, open(a.out, "wb"))


if __name__ == "__main__":
    main()
