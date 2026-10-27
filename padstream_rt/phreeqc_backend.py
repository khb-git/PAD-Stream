"""PHREEQC chemistry backend (speciation, mineral equilibrium, CO2 solubility).

Implements the ``ChemistryBackend`` interface of chemistry.py on top of the
USGS IPHREEQC engine (Python bindings: ``pip install phreeqc``; databases are
the ones distributed with PHREEQC).

* Component basis: PHREEQC element names (e.g. "Ca", "Mg", "Fe", "Na", "K",
  "Cl", "C", "Si", "Al", "S").  H, O and charge are closed by PHREEQC (pH by
  charge balance), so element totals are the transported quantities.
* Mineral stoichiometry ``nu`` is derived from the database itself: 1 mol of
  each phase is dissolved into pure water and the element totals are read
  back.  The extents xi returned to the coupling are PHREEQC's own phase
  deltas, so the mass balance in coupling.py stays exact.
* Equilibrium cells: EQUILIBRIUM_PHASES with target SI = 0 for the routed
  minerals.  Kinetic cells: PHREEQC speciation gives pH and saturation indices;
  the Palandri & Kharaka rate law (kinetics.py) gives the rate; the extent is
  capped by the PHREEQC equilibrium extent so no mineral overshoots.
* CO2 solubility: brine equilibrated with CO2(g) at a given fugacity.  In
  EQUILIBRIUM_PHASES PHREEQC takes the target as a partial pressure and applies
  its own Peng-Robinson fugacity coefficient (verified 26 Oct 2026: target
  log10 P gives SI = log10(phi P)).  A target fugacity is therefore converted
  to the pure-CO2 partial pressure with the same fugacity, using PHREEQC's CO2
  critical constants.

Accuracy of dissolved CO2 against Duan & Sun (2003, Tables 3-5; 22 points,
30-120 C, 50-300 bar, 0-2 m NaCl): pitzer.dat mean 3.3 % / max 9.2 %;
phreeqc.dat mean 5.0 % / max 12.5 % (error grows with salinity).  phreeqc.dat
is the default because pitzer.dat lacks aluminosilicates (feldspars, clays).
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from .chemistry import ChemInput
from .kinetics import mineral_rate
from .pvt import Fluid, phase_props
from .state import ChemicalSystem, Mineral

ATM = 101325.0
# Transported totals carry no redox state.  Entered as a plain total, PHREEQC
# would split Fe between Fe(2) and Fe(3) at the default pe 4, i.e. oxidise it
# at every call, which makes siderite look strongly undersaturated (found
# 27 Oct 2026: explicit re-speciation dissolved 30x more siderite than PHREEQC
# KINETICS, which keeps the redox state during the reaction).  Deep saline
# reservoirs are reducing, so dissolved iron is entered as Fe(2).
REDOX_INPUT = {"Fe": "Fe(2)"}
# CO2(g) constants as given in phreeqc.dat / pitzer.dat (T_c 304.2 K, P_c 72.86 atm, omega 0.225)
CO2_PHREEQC = Fluid(["CO2"], [304.2], [72.86 * ATM], [0.225], [0.04401])


def _phreeqc(database: str):
    from phreeqc import Phreeqc
    p = Phreeqc()
    if p.LoadBuiltInDatabase(database):
        raise RuntimeError(p.GetErrorString())
    return p


class PhreeqcBackend:
    def __init__(self, elements: Sequence[str], phases: Sequence[str],
                 kinetic_params: Optional[Dict[str, dict]] = None,
                 specific_area: Optional[Dict[str, float]] = None,
                 molar_volume: Optional[Dict[str, float]] = None,
                 database: str = "phreeqc.dat", water_density: float = 1000.0):
        self.db = database
        self.elements = list(elements)
        self.phases = list(phases)
        self.rho_w = water_density
        self.nu = self._derive_stoichiometry()
        kp = kinetic_params or {}
        sa = specific_area or {}
        vm = molar_volume or {}
        self.minerals = [Mineral(name, list(self.nu[j]), vm.get(name, 3.7e-5), 0.0,
                                 specific_area=sa.get(name, 1.0e3),
                                 **(kp.get(name) or dict(log10_k25_neutral=-99.0, E_neutral=0.0)))
                         for j, name in enumerate(self.phases)]

    # ------------------------------------------------------------------
    def chemical_system(self, c_eq_scale=None) -> ChemicalSystem:
        return ChemicalSystem(self.elements, self.minerals,
                              c_eq_scale=None if c_eq_scale is None else np.asarray(c_eq_scale, float))

    def _derive_stoichiometry(self) -> np.ndarray:
        nu = np.zeros((len(self.phases), len(self.elements)))
        for j, ph in enumerate(self.phases):
            p = _phreeqc(self.db)
            tot = "\n".join(f"10{i} PUNCH TOT(\"{e}\")*TOT(\"water\")" for i, e in enumerate(self.elements))
            inp = f"""SOLUTION 1
 pH 7 charge
REACTION 1
 {ph} 1.0
 1 mol
USER_PUNCH
 -headings {' '.join(self.elements)}
{tot}
SELECTED_OUTPUT
 -reset false
END"""
            if p.RunString(inp):
                raise RuntimeError(f"{ph}: {p.GetErrorString()}")
            out = p.GetSelectedOutput()
            nu[j] = [float(out[e][-1]) for e in self.elements]
        return np.round(nu, 10)

    # ------------------------------------------------------------------
    def _solution_block(self, k, n_aq_row, v_brine, T, P):
        kgw = max(v_brine * self.rho_w, 1e-12)
        lines = [f"SOLUTION {k}", f" temp {T - 273.15:.6f}", f" pressure {P / ATM:.6f}",
                 " units mol/kgw", f" -water {kgw:.10g}", " pH 7 charge"]
        for e, n in zip(self.elements, n_aq_row):
            m = n / kgw
            if m > 1e-15:
                lines.append(f" {REDOX_INPUT.get(e, e)} {m:.12g}")
        return "\n".join(lines)

    def _run(self, blocks: List[str], punch_sel: str):
        p = _phreeqc(self.db)
        # SELECTED_OUTPUT must be defined before the first simulation
        inp = punch_sel + "\n" + "\n".join(blocks)
        if p.RunString(inp):
            raise RuntimeError(p.GetErrorString()[:2000])
        return p.GetSelectedOutput()

    def speciate(self, x: ChemInput):
        """pH and log10 Omega (n, nmin) per cell."""
        n = x.n_aq.shape[0]
        blocks = [self._solution_block(k + 1, x.n_aq[k], x.v_brine[k], x.T[k], x.P[k]) + "\nEND"
                  for k in range(n)]
        sel = ("SELECTED_OUTPUT\n -reset false\n -pH true\n -saturation_indices "
               + " ".join(self.phases) + "\n")
        out = self._run(blocks, sel)
        pH = np.array(out["pH"], float)[-n:]
        si = np.column_stack([np.array(out[f"si_{ph}"], float)[-n:] for ph in self.phases])
        return pH, si

    def equilibrium(self, x: ChemInput) -> np.ndarray:
        n = x.n_aq.shape[0]
        act = x.mask()
        blocks = []
        for k in range(n):
            eq = [f"EQUILIBRIUM_PHASES {k + 1}"]
            for j, ph in enumerate(self.phases):
                if act[k, j]:
                    eq.append(f" {ph} 0 {max(x.n_min[k, j], 0.0):.12g}")
            blocks.append(self._solution_block(k + 1, x.n_aq[k], x.v_brine[k], x.T[k], x.P[k])
                          + "\n" + "\n".join(eq) + "\nEND")
        sel = ("SELECTED_OUTPUT\n -reset false\n -state true\n -equilibrium_phases "
               + " ".join(self.phases) + "\n")
        out = self._run(blocks, sel)
        state = out["state"]
        rows = [i for i, s in enumerate(state) if str(s).strip() == "react"]
        xi = np.zeros((n, len(self.phases)))
        for j, ph in enumerate(self.phases):
            col = np.array([out[f"d_{ph}"][i] for i in rows], float)
            xi[:, j] = -col                      # d_phase < 0 means it dissolved
        return np.where(act, xi, 0.0)

    def _rates_block(self) -> str:
        """PHREEQC RATES for the Palandri & Kharaka (2004) law of every phase:
        r = A0 (M/M0)^(2/3) * sum_mech k_mech(T) a_H+^n_mech * sgn(d)|d|^eta,
        d = 1 - SR^theta.  Positive = dissolution (mol/s)."""
        lines = ["RATES"]
        for m in self.minerals:
            def term(lk, E, n, act):
                if lk is None:
                    return "0"
                a = "" if act is None else f" * ACT(\"H+\")^({n})"
                return f"10^({lk}) * EXP(-({E or 0.0}) / 8.314462618 * (1 / TK - 1 / 298.15)){a}"
            k = " + ".join([term(m.log10_k25_neutral, m.E_neutral, 0, None),
                            term(m.log10_k25_acid, m.E_acid, m.n_acid, "H"),
                            term(m.log10_k25_base, m.E_base, m.n_base, "H")])
            lines += [m.name, "-start",
                      "10 IF (M0 <= 0) THEN GOTO 200",
                      f"20 kk = {k}",
                      f"30 d = 1 - SR(\"{m.name}\")^{m.theta}",
                      f"40 rate = PARM(1) * (M / M0)^(2/3) * kk * SGN(d) * ABS(d)^{m.eta}",
                      "50 IF (rate > 0) AND (M <= 0) THEN rate = 0",
                      "60 SAVE rate * TIME", "70 END",
                      "200 SAVE 0", "-end"]
        return "\n".join(lines)

    def kinetic(self, x: ChemInput, tol: float = 1e-8, cvode: bool = True) -> np.ndarray:
        """Kinetic extents integrated by PHREEQC itself (KINETICS + RATES;
        CVODE stiff solver by default, error-controlled Runge-Kutta with
        ``cvode=False``), so saturation indices are updated
        inside the step and no mineral can overshoot equilibrium or drive an
        element negative.  This is the reference for the surrogate."""
        n = x.n_aq.shape[0]
        act = x.mask()
        blocks = []
        for k in range(n):
            kin = []
            for j, m in enumerate(self.minerals):
                if act[k, j] and x.n_min[k, j] > 0 and x.area[k, j] > 0:
                    nm = x.n_min[k, j]
                    kin += [m.name, f" -m {nm:.12g}", f" -m0 {nm:.12g}",
                            f" -parms {x.area[k, j] * x.v_bulk:.12g}", f" -tol {tol:g}"]
            if not kin:
                kin = [self.minerals[0].name, " -m 0", " -m0 0", " -parms 0"]
            blocks.append(self._solution_block(k + 1, x.n_aq[k], x.v_brine[k], x.T[k], x.P[k])
                          + f"\nKINETICS {k + 1}\n" + "\n".join(kin)
                          + f"\n -steps {x.dt:.10g}\n -cvode {'true' if cvode else 'false'}"
                          + "\n -bad_step_max 5000\nEND")
        names = " ".join(m.name for m in self.minerals)
        sel = (self._rates_block() + "\nSELECTED_OUTPUT\n -reset false\n -sim true\n -state true\n"
               " -step true\n -kinetic_reactants " + names + "\n")
        out = self._run(blocks, sel)
        sims = np.array(out["sim"], int)
        state = [str(s).strip() for s in out["state"]]
        xi = np.zeros((n, len(self.minerals)))
        last = {}
        for i, (sm, stt) in enumerate(zip(sims, state)):
            if stt == "react":
                last[sm] = i
        for k in range(n):
            i = last.get(k + 1)
            if i is None:
                continue
            for j, m in enumerate(self.minerals):
                d = float(out[f"dk_{m.name}"][i])
                xi[k, j] = -d                         # dk < 0: reactant consumed (dissolved)
        return np.where(act, xi, 0.0)

    def kinetic_explicit(self, x: ChemInput) -> np.ndarray:
        """One explicit PK step with a joint-equilibrium cap (v0.2 behaviour).
        Not conservative of positivity when several minerals share elements;
        kept for comparison only."""
        pH, si = self.speciate(x)
        omega = 10.0 ** si
        rate = np.column_stack([mineral_rate(m, x.area[:, j], x.T, pH, omega[:, j])
                                for j, m in enumerate(self.minerals)])
        xi = rate * x.v_bulk * x.dt
        cap = self.equilibrium(x)                # never step past equilibrium
        xi = np.where(xi >= 0, np.minimum(xi, np.maximum(cap, 0.0)),
                      np.maximum(xi, np.minimum(cap, 0.0)))
        xi = np.minimum(xi, x.n_min)             # cannot dissolve more than is there
        return np.where(x.mask(), xi, 0.0)

    def pH(self, n_aq, v_brine, T=323.15, P=1e7):
        n = n_aq.shape[0]
        T = np.broadcast_to(T, (n,)); P = np.broadcast_to(P, (n,))
        x = ChemInput(n_aq, np.zeros((n, len(self.phases))), v_brine, 1.0,
                      np.zeros((n, len(self.phases))), np.asarray(T, float), np.asarray(P, float), 0.0)
        return self.speciate(x)[0]

    # ------------------------------------------------------------------
    @staticmethod
    def partial_pressure_for_fugacity(f_co2, T):
        """Pure-CO2 pressure (Pa) whose PR fugacity equals f_co2 (Pa), PHREEQC constants."""
        f = np.atleast_1d(np.asarray(f_co2, float))
        T = np.broadcast_to(np.asarray(T, float), f.shape)
        p = f.copy()
        for _ in range(60):
            _, lp = phase_props(CO2_PHREEQC, np.ones((f.size, 1)), T, p, "stable")
            g = p * np.exp(lp[:, 0]) - f
            dp = 1e-4 * p
            _, lp2 = phase_props(CO2_PHREEQC, np.ones((f.size, 1)), T, p + dp, "stable")
            dg = ((p + dp) * np.exp(lp2[:, 0]) - (p * np.exp(lp[:, 0]))) / dp
            step = g / dg
            p = np.clip(p - step, 1.0, None)
            if np.max(np.abs(step / p)) < 1e-10:
                break
        return p

    def co2_saturation(self, n_aq, v_brine, T, P, f_co2):
        """Moles of CO2 the brine of each cell takes up when equilibrated with CO2
        at fugacity ``f_co2`` (Pa); negative values mean the brine degasses."""
        n = n_aq.shape[0]
        pp = self.partial_pressure_for_fugacity(f_co2, T)
        blocks = []
        for k in range(n):
            blocks.append(self._solution_block(k + 1, n_aq[k], v_brine[k], T[k], P[k])
                          + f"\nEQUILIBRIUM_PHASES {k + 1}\n CO2(g) {math.log10(pp[k] / ATM):.10f} 1e6\nEND")
        sel = "SELECTED_OUTPUT\n -reset false\n -state true\n -equilibrium_phases CO2(g)\n"
        out = self._run(blocks, sel)
        rows = [i for i, s in enumerate(out["state"]) if str(s).strip() == "react"]
        return -np.array([out["d_CO2(g)"][i] for i in rows], float)
