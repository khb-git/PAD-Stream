"""Routing ablation on one Mt. Simon-complex layer (claim 1 + claim 2 experiment).

``--system lower_mt_simon`` (default) or ``--system argenta`` (carbonate-bearing).

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
  da_step      Damkohler routing + learned PHREEQC KINETICS step (StepSurrogate)
               with PHREEQC-speciation checks and reference fallback
  da_stiff_S   Damkohler routing (skip / equilibrium) + stiff_surr_S for the
               KINETIC pairs: the full four-way router
  *_eqfirst    any config with the v0.3.0 split order (equilibrium pairs
               before kinetic pairs; default is kinetic first)
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
from padstream_rt.mineralogy import (CLAY, DENSITY_G_CM3, brine_solution_lines, c_eq_scales, load_brine,
                                     unit_mineralogy)
from padstream_rt.phreeqc_backend import ATM, _phreeqc
from padstream_rt.state import MD_TO_M2
from padstream_rt.surrogate import MLP, TRACE_MOLAL, SpeciationSurrogate, trace_elements

# Reacting systems.  XRD = Freiburg et al. (2022) Table 1 class for each phase
# (None = not in the rock: seeded at a small volume fraction, assumed).  Pyrite and
# hematite are left inert (redox rate laws not modelled).  Molar masses follow the
# phreeqc.dat formulae.
SYSTEMS = {
    "lower_mt_simon": dict(
        unit="Lower Mt. Simon", grain=None,
        elements=["Na", "K", "Mg", "Fe", "Al", "Si", "C", "Cl"],
        phases=["Quartz", "K-feldspar", "Albite", "Siderite", "Illite", "Kaolinite"],
        xrd=["quartz", "k_feldspar", "plagioclase", "siderite", "illite_mica", None],
        pk=["quartz", "K-feldspar", "albite", "siderite (provisional; Sun et al. 2020 Table 4)",
            "illite (provisional; Sun et al. 2020 Table 4)", "kaolinite"],
        formation_eq=["Quartz", "Kaolinite", "K-feldspar"],
        secondaries=["Kaolinite", "Quartz"]),
    # Same rock with the Liu et al. (2011) Na-Ca-Mg-Cl-SO4 brine: Ca and S become
    # transported components and calcite / anhydrite can form (seeded, assumed).
    "lower_mt_simon_brine": dict(
        unit="Lower Mt. Simon", grain=None, brine="liu2011_mt_simon_brine",
        elements=["Na", "K", "Mg", "Ca", "Fe", "Al", "Si", "C", "S", "Cl"],
        phases=["Quartz", "K-feldspar", "Albite", "Siderite", "Illite", "Kaolinite", "Calcite", "Anhydrite"],
        xrd=["quartz", "k_feldspar", "plagioclase", "siderite", "illite_mica", None, None, None],
        pk=["quartz", "K-feldspar", "albite", "siderite (provisional; Sun et al. 2020 Table 4)",
            "illite (provisional; Sun et al. 2020 Table 4)", "kaolinite", "calcite", "anhydrite"],
        # measured brine kept as given (incl. its dissolved C); only Si and Al are set by
        # quartz and kaolinite.  Forcing K-feldspar equilibrium at 50 C dissolved
        # ~0.1 mol/kgw of feldspar, i.e. it contradicted the measured K.
        formation_eq=["Quartz", "Kaolinite"], formation_log_pco2=None,
        secondaries=["Kaolinite", "Quartz", "Calcite", "Anhydrite"],
        dissolution_only=["K-feldspar", "Albite", "Illite"],
        # 1e-4 seeds of calcite/anhydrite simply dissolved in the acid front and
        # inflated the porosity change ~6x; 1e-6 removes that artefact
        seed_vf=1e-6),
    # Argenta: Freiburg et al. 2022 give "very fine sandstone to pebble" (p. 11);
    # pebble is outside the Wentworth table, so very fine to very coarse is ASSUMED.
    "argenta": dict(
        unit="Argenta", grain="very fine to very coarse",
        elements=["Na", "K", "Mg", "Ca", "Al", "Si", "C", "Cl"],
        phases=["Quartz", "K-feldspar", "Calcite", "Dolomite", "Illite", "Kaolinite", "Chlorite(14A)"],
        xrd=["quartz", "k_feldspar", "calcite", "dolomite", "illite_mica", "kaolinite", "chlorite"],
        pk=["quartz", "K-feldspar", "calcite", "dolomite (disordered)",
            "illite (provisional; Sun et al. 2020 Table 4)", "kaolinite", "chlorite"],
        formation_eq=["Quartz", "Kaolinite", "K-feldspar", "Calcite", "Dolomite"],
        secondaries=["Kaolinite", "Quartz", "Calcite"],
        # ASSUMED: no kinetic precipitation of the primary silicates.  With the
        # symmetric PK law, illite precipitation on 1-um geometric clay areas in
        # fully acidified brine stalled PHREEQC KINETICS (> 4 min per cell).
        dissolution_only=["K-feldspar", "Illite", "Chlorite(14A)"]),
}
SYSTEMS["argenta_brine"] = dict(SYSTEMS["argenta"], brine="liu2011_mt_simon_brine",
                                formation_eq=["Quartz", "Kaolinite", "Calcite", "Dolomite"],
                                formation_log_pco2=None,
                                elements=["Na", "K", "Mg", "Ca", "Al", "Si", "C", "S", "Cl"],
                                phases=SYSTEMS["argenta"]["phases"] + ["Anhydrite"],
                                xrd=SYSTEMS["argenta"]["xrd"] + [None],
                                pk=SYSTEMS["argenta"]["pk"] + ["anhydrite"],
                                secondaries=SYSTEMS["argenta"]["secondaries"] + ["Anhydrite"],
                                seed_vf=1e-6)
MOLAR_MASS = {"Anhydrite": 136.14, "Quartz": 60.08, "K-feldspar": 278.33, "Albite": 262.22, "Siderite": 115.85,
              "Illite": 389.34, "Kaolinite": 258.16, "Calcite": 100.09, "Dolomite": 184.40,
              "Chlorite(14A)": 555.80}
XRD_DENS = {"Anhydrite": "anhydrite", "Quartz": "quartz", "K-feldspar": "k_feldspar", "Albite": "plagioclase",
            "Siderite": "siderite", "Illite": "illite_mica", "Kaolinite": "kaolinite",
            "Calcite": "calcite", "Dolomite": "dolomite", "Chlorite(14A)": "chlorite"}


def select_system(name):
    global SYSTEM, ELEMENTS, PHASES, XRD, PK
    SYSTEM = SYSTEMS[name]
    ELEMENTS, PHASES, XRD, PK = (SYSTEM[k] for k in ("elements", "phases", "xrd", "pk"))


select_system("lower_mt_simon")
STEP_MODEL = dict(net=None, box=None,
                  kinetic=["Quartz", "K-feldspar", "Albite", "Siderite", "Illite"])
T_K, P_PA, NACL, LOG_PCO2_INJ = 323.15, 15e6, 2.0, 1.9
BRINE_PH = 6.9            # Liu et al. 2011, Table 3


def brine_totals(log_pco2, phases_eq=()):
    """mol per m^3 brine of each element for 2 m NaCl, or the system's brine, at (T, P)."""
    p = _phreeqc("phreeqc.dat")
    eq = "\n".join(([f" CO2(g) {log_pco2} 100"] if log_pco2 is not None else [])
                   + [f" {ph} 0 10" for ph in phases_eq])
    tr = "\n".join(f" {e} {TRACE_MOLAL}" for e in trace_elements(ELEMENTS))
    brine = load_brine(SYSTEM["brine"]) if SYSTEM.get("brine") else None
    sol = "\n".join(brine_solution_lines(NACL, brine))
    if brine is not None:     # trace only what the brine lacks
        tr = "\n".join(f" {e} {TRACE_MOLAL}" for e in trace_elements(ELEMENTS)
                       if e.split("(")[0] not in brine)
    inp = (f"SELECTED_OUTPUT\n -reset false\nUSER_PUNCH\n -headings {' '.join(ELEMENTS)}\n"
           + "\n".join(f"{10 + i} PUNCH TOT(\"{e}\")" for i, e in enumerate(ELEMENTS))
           + f"\nSOLUTION 1\n temp {T_K - 273.15}\n pressure {P_PA / ATM}\n units mol/kgw\n pH 7 charge\n"
             f"{sol}\n{tr}\nEQUILIBRIUM_PHASES 1\n{eq}\nEND")
    if brine is not None:   # measured pH, charge closed on Cl (brine_solution_lines)
        inp = inp.replace(" pH 7 charge\n", f" pH {BRINE_PH}\n")
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


def build(roughness=1.0, seed=3, nx=25, clay_roughness=0.01, allow_precipitation=False, seed_vf=None):
    if seed_vf is None:
        seed_vf = SYSTEM.get("seed_vf", 1e-4)
    um = unit_mineralogy(SYSTEM["unit"], grain_size_text=SYSTEM["grain"], roughness=roughness)
    vf, spec = {}, {}
    for ph, x in zip(PHASES, XRD):
        if x is None:
            vf[ph], spec[ph] = seed_vf, 6.0 / 1e-6 * roughness    # secondary seed (assumed)
        else:
            i = um.minerals.index(x)
            vf[ph], spec[ph] = um.vf_bulk[i], um.specific_area[i]
        if (x or "") in CLAY or ph == "Kaolinite":   # clay-only area factor (sensitivity)
            spec[ph] *= clay_roughness
    kp = {ph: load_pk_parameters(n) for ph, n in zip(PHASES, PK)}
    vm = {ph: MOLAR_MASS[ph] / DENSITY_G_CM3[XRD_DENS[ph]] * 1e-6 for ph in PHASES}
    phq = PhreeqcBackend(ELEMENTS, PHASES, kinetic_params=kp, specific_area=spec, molar_volume=vm,
                         dissolution_only=() if allow_precipitation else SYSTEM.get("dissolution_only", ()))
    ceq = c_eq_scales(PHASES, T_K, P_PA, NACL, 10 ** LOG_PCO2_INJ,
                      brine=load_brine(SYSTEM["brine"]) if SYSTEM.get("brine") else None)
    system = phq.chemical_system(ceq)
    geom = GridGeometry(nx=nx, ny=nx, nz=1)
    n = geom.ncell
    rng = np.random.default_rng(seed)
    st = ReactiveState(geom, system, porosity=um.porosity,
                       perm=np.repeat(rng.lognormal(np.log(110), 0.6, n)[:, None], 3, 1) * MD_TO_M2,
                       brine_saturation=0.6,
                       total_aq=np.tile(brine_totals(SYSTEM.get("formation_log_pco2", -1.0), SYSTEM["formation_eq"]), (n, 1)),
                       mineral_vf=np.tile([vf[p] for p in PHASES], (n, 1)),
                       temperature=T_K, pressure=P_PA)
    frac = nx * nx / 2500.0                     # same flux per unit area as the 50 x 50 layer
    op = TransferOperator(geom, synthetic_bundle(geom, nsl=max(int(400 * nx / 50), 50),
                                                 total_q=714.29 / 86400 / 15 * frac),
                          st.porosity * geom.cell_volume)
    return phq, st, op, brine_totals(LOG_PCO2_INJ)


def run(config, phq, st0, op0, c_in, net, steps, dt, da_eq=10.0, da_skip=1e-3, chem_substeps=1):
    # suffix "_eqfirst": the v0.3.0 split order (equilibrium pairs, then kinetic)
    chem_order = ("kinetic", "equilibrium")
    if config.endswith("_eqfirst"):
        config, chem_order = config[:-len("_eqfirst")], ("equilibrium", "kinetic")
    st, op = copy.deepcopy(st0), copy.deepcopy(op0)
    sb = st.brine_saturation
    fb = sb ** 2 / (sb ** 2 + 0.1 * (1 - sb) ** 2)
    stiff_max = (float(config.split("_")[-1])
                 if config.startswith(("stiff_surr_", "da_stiff_")) else None)
    surr = (SpeciationSurrogate(net, phq.minerals, ELEMENTS, stiff_max=stiff_max)
            if net is not None else None)
    T, P = st.temperature, st.pressure
    surrogate = config in ("aposteriori", "da_surr", "da_sat_surr") or stiff_max is not None
    if config == "da_step":                    # learned PHREEQC step + reference checks
        from padstream_rt.surrogate import StepSurrogate
        box = np.load(STEP_MODEL["box"])
        step = StepSurrogate(MLP.load(STEP_MODEL["net"]), phq.nu, ELEMENTS, PHASES, STEP_MODEL["kinetic"],
                             box["x_min"], box["x_max"],
                             speciate_fn=phq.speciate if STEP_MODEL.get("with_si", True) else None)
        # keep_training_data: the rejected / routed cells and their PHREEQC extents
        # (harvested for focused retraining, examples/harvest_step_states.py)
        tol = STEP_MODEL.get("omega_tol", 0.05)   # SI sign-flip tolerance, repair and check (section 13)
        step.omega_tol = STEP_MODEL.get("repair_tol", tol)
        backend = SurrogateBackend(step, phq, keep_training_data=bool(STEP_MODEL.get("harvest")),
                                   omega_tol=tol)
        spec = lambda a, v: phq.speciate(ChemInput(a, np.zeros((len(v), len(PHASES))), v, 1.0,
                                                   np.zeros((len(v), len(PHASES))), T, P, 0.0))
    elif surrogate:
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
               "da_ref": da, "da_step": da, "da_surr": da, "da_sat_ref": da, "da_sat_surr": da}.get(
                   config, da if config.startswith("da_stiff_") else off)
    t_chem, mass_err, counts, ref_cells = 0.0, 0.0, [], 0
    failed = None
    for k in range(steps):
        t0 = time.perf_counter()
        try:
            rep = reactive_step(st, op, backend, dt, fb, c_inlet=c_in, routing=routing, pH_fn=pH_fn,
                                spec_fn=spec_fn, chem_order=chem_order,
                                chem_substeps=1 if chem_order[0] == "equilibrium" else chem_substeps)
        except RuntimeError as e:                       # PHREEQC did not converge
            failed = (k, str(e).strip().splitlines()[-1][:160])
            break
        t_chem += time.perf_counter() - t0
        mass_err = max(mass_err, float(np.abs(rep.mass_balance_error).max()))
        print(f"  [{config}] step {k + 1}/{steps}: {time.perf_counter() - t0:.1f} s", flush=True)
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
                surr_cells=None if stats is None else stats.cells,
                buffer=getattr(backend, "training_buffer", None),
                kinetic_offered=None if stats is None else stats.offered.get("kinetic", 0),
                kinetic_accepted=None if stats is None else stats.accepted.get("kinetic", 0))


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
    ap.add_argument("--clay_roughness", type=float, default=0.01,
                    help="factor on the geometric area of clay phases only (illite, kaolinite, chlorite, ...)")
    ap.add_argument("--dissolution_only", default=None,
                    help="comma list overriding the system's dissolution_only minerals")
    ap.add_argument("--step_net", default=None, help="step-surrogate network (.npz) for config da_step")
    ap.add_argument("--step_box", default=None, help="training feature box (.npz) for da_step")
    ap.add_argument("--step_kinetic", default=None,
                    help="comma list of the minerals the step network predicts (default: lower Mt. Simon set)")
    ap.add_argument("--omega_tol", default="0.05",
                    help="da_step: SI sign-flip tolerance of the overshoot repair and check: a number, "
                         "inf (no check), or cal (per mineral, from <step_net>_tol.json; section 13)")
    ap.add_argument("--seed_vf", type=float, default=None,
                    help="volume fraction given to secondary phases absent from the rock "
                         "(default: the system's seed_vf, else 1e-4)")
    ap.add_argument("--allow_precipitation", action="store_true",
                    help="ignore the system's dissolution_only list (symmetric PK law for every mineral)")
    ap.add_argument("--reference", default="truth",
                    help="config the others are compared with (da_ref when full kinetics is too slow)")
    ap.add_argument("--system", default="lower_mt_simon", choices=sorted(SYSTEMS))
    ap.add_argument("--cache", default="ablation_cache", help="prefix for cached truth / all_eq runs")
    ap.add_argument("--da_eq", type=float, default=10.0)
    ap.add_argument("--da_skip", type=float, default=1e-3)
    ap.add_argument("--chem_substeps", type=int, default=1,
                    help="kinetic/equilibrium alternations per step (the _eqfirst configs always use 1)")
    a = ap.parse_args()
    select_system(a.system)
    if a.omega_tol == "cal":
        import json
        cal = json.load(open(a.step_net[:-4] + "_tol.json"))
        tol = np.array([float(cal.get(p, 0.05)) for p in PHASES])
    else:
        tol = float(a.omega_tol)
    STEP_MODEL.update(net=a.step_net, box=a.step_box, omega_tol=tol)
    if a.step_kinetic:
        STEP_MODEL["kinetic"] = a.step_kinetic.split(",")
    if a.dissolution_only is not None:
        SYSTEM["dissolution_only"] = [m for m in a.dissolution_only.split(",") if m]
    net = None
    if a.net:
        net = MLP.load(a.net) if a.net.endswith(".npz") else MLP.from_state(pickle.load(open(a.net, "rb")))
    phq, st0, op0, c_in = build(a.roughness, nx=a.nx, clay_roughness=a.clay_roughness,
                                allow_precipitation=a.allow_precipitation, seed_vf=a.seed_vf)
    a.seed_vf = a.seed_vf if a.seed_vf is not None else SYSTEM.get("seed_vf", 1e-4)
    dt = a.dt_days * 86400.0
    results = {}
    for cfg in a.configs.split(","):
        cache = f"{a.cache}_{a.system}_{cfg}_cs{a.chem_substeps}_nx{a.nx}_s{a.steps}_dt{a.dt_days:g}_r{a.roughness:g}_cr{a.clay_roughness:g}_p{int(a.allow_precipitation)}_do{len(SYSTEM.get("dissolution_only", ()))}_sv{a.seed_vf:g}.pkl" if a.cache else None
        if cfg in ("truth", "all_eq", "da_ref") and cache and os.path.exists(cache):
            results[cfg] = pickle.load(open(cache, "rb"))
        else:
            results[cfg] = run(cfg, phq, st0, op0, c_in, net, a.steps, dt, a.da_eq, a.da_skip, a.chem_substeps)
            if cfg in ("truth", "all_eq", "da_ref") and cache:
                pickle.dump(results[cfg], open(cache, "wb"))
        r = results[cfg]
        if r["failed"]:
            print(f"{cfg:12s} FAILED at step {r['failed'][0]}: {r['failed'][1]}", flush=True)
            continue
        print(f"{cfg:12s} chem+transport {r['time']:7.1f} s  PHREEQC cell-solves {r['ref_cells']}  "
              f"(routed a priori {r.get('routed')})  max|mass err| {r['mass_err']:.1e}  "
              f"fallback {r['fallback']}  {r['reasons'] or ''}", flush=True)
        if r.get("kinetic_offered"):
            print(f"{cfg:12s} kinetic cells on the surrogate {r['kinetic_accepted']} / {r['kinetic_offered']} "
                  f"({r['kinetic_accepted'] / r['kinetic_offered']:.1%})", flush=True)
    summary = {}
    for cfg, r in results.items():
        if cfg == a.reference or r["failed"]:
            summary[cfg] = dict(failed=r["failed"]) if r["failed"] else summary.get(cfg)
            continue
        c = compare(r, results[a.reference], st0)
        summary[cfg] = dict(ref_cells=r["ref_cells"], time=r["time"], mass_err=r["mass_err"], fallback=r["fallback"],
                            reasons=r["reasons"], **c, last_regimes=r["per_mineral"][-1])
        print(f"{cfg:12s} d(mineral vol) err {c['dvf_rel_L1']:.2e}  dphi err {c['dphi_rel_L1']:.2e}  dC err {c['dC_rel_L1']:.2e}  "
              f"mineral err {dict(zip(PHASES, np.round(c['mineral_rel_L1'], 4)))}")
    ref = results[a.reference]
    summary[a.reference] = dict(time=ref["time"], mass_err=ref["mass_err"], last_regimes=ref["per_mineral"][-1],
                                dphi_max=float(np.abs(ref["state"].porosity - st0.porosity).max()))
    print(f"{a.reference} max |dphi|", summary[a.reference]["dphi_max"])
    for cfg in ("da_ref", "da_surr", "da_sat_ref", "da_sat_surr"):
        if cfg in results:
            print(cfg, "final regimes", results[cfg]["per_mineral"][-1])
    if a.out:
        pickle.dump(summary, open(a.out, "wb"))


if __name__ == "__main__":
    main()
