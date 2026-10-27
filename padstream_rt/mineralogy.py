"""Mt. Simon mineralogy -> mineral volume fractions, reactive areas, c_eq scales.

Source data (in ``data/``):

* ``freiburg_2022_mt_simon_mineralogy.csv`` - Freiburg et al. (2022), Marine
  and Petroleum Geology 146, 105963, Table 1 (p. 6): whole-rock XRD in wt %,
  with the clay species given as % of total clay.
* ``freiburg_2022_reservoir_properties.csv`` - same paper, Table 3 (p. 12):
  porosity and permeability of the IBDP core samples, plus the petrographic
  grain-size descriptions (pp. 10-11).

What is NOT in Freiburg et al. (2022) and is therefore an explicit,
replaceable assumption here (every one is a keyword argument):

* mineral densities (``DENSITY_G_CM3``: typical handbook values, to be
  replaced by molar volumes from the thermodynamic database in use);
* the grain diameter for each Wentworth class (class bounds only; the paper
  gives a verbal class, not a measured size);
* the clay particle size (equivalent sphere of 1 um, the middle of the
  2.0-0.2 um fractions the paper separated; no measured clay surface area);
* a surface-roughness / reactive-fraction factor (default 1, i.e. geometric).
  Geometric areas are known to overestimate field-scale reactive areas, so this
  factor is one of the sensitivity parameters of the routing experiment.

c_eq scales need a brine composition, which Freiburg et al. (2022) do not
report; ``c_eq_scales`` takes the NaCl molality as a required argument.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np

_DATA = Path(__file__).with_name("data")

NON_CLAY = ["quartz", "k_feldspar", "plagioclase", "calcite", "siderite",
            "dolomite", "pyrite", "hematite"]
CLAY = ["smectite", "illite_smectite", "illite_mica", "kaolinite", "chlorite"]

# ASSUMED typical densities, g/cm^3 (not from Freiburg et al. 2022).
DENSITY_G_CM3 = dict(quartz=2.65, k_feldspar=2.56, plagioclase=2.62, calcite=2.71,
                     siderite=3.96, dolomite=2.84, pyrite=5.01, hematite=5.26,
                     smectite=2.35, illite_smectite=2.60, illite_mica=2.75,
                     kaolinite=2.60, chlorite=2.65)

# Wentworth (1922) class bounds in mm; the geometric mean of each class is used.
WENTWORTH_MM = {"very fine": (0.0625, 0.125), "fine": (0.125, 0.25), "medium": (0.25, 0.5),
                "coarse": (0.5, 1.0), "very coarse": (1.0, 2.0)}

# PHREEQC (phreeqc.dat) phase used as the reacting proxy for each XRD class.
PHREEQC_PHASE = dict(quartz="Quartz", k_feldspar="K-feldspar", plagioclase="Albite",
                     calcite="Calcite", siderite="Siderite", dolomite="Dolomite",
                     pyrite="Pyrite", hematite="Hematite", illite_mica="Illite",
                     illite_smectite="Illite", kaolinite="Kaolinite", chlorite="Chlorite(14A)")


def _rows(name):
    with open(_DATA / name, newline="") as f:
        return list(csv.DictReader(r for r in f if not r.startswith("#")))


def load_freiburg_table1() -> Dict[str, Dict[str, float]]:
    """{unit: {mineral: wt % of whole rock}} with the clay split applied."""
    out = {}
    for r in _rows("freiburg_2022_mt_simon_mineralogy.csv"):
        d = {m: float(r[m]) for m in NON_CLAY}
        clay = float(r["total_clay"])
        split = np.array([float(r[m]) for m in CLAY])
        # Most rows give the clay species as % of total clay (sum ~100); the
        # New Albany row sums to its total clay (49) instead, i.e. whole-rock wt %.
        if abs(split.sum() - 100.0) > abs(split.sum() - clay):
            split = 100.0 * split / clay
        d.update({m: clay * x / 100.0 for m, x in zip(CLAY, split)})
        out[r["unit"]] = d
    return out


def load_freiburg_table3():
    """List of sample dicts (unit, depth_m, porosity [-], permeability_mD or None, grain_size_text)."""
    out = []
    for r in _rows("freiburg_2022_reservoir_properties.csv"):
        k = r["permeability_mD"]
        out.append(dict(unit=r["unit"], depth_m=float(r["depth_m"]),
                        porosity=float(r["porosity_pct"]) / 100.0,
                        permeability_mD=None if k.startswith("<") else float(k),
                        classification=r["classification"], grain_size_text=r["grain_size_text"]))
    return out


def grain_diameter_m(text: str) -> float:
    """Diameter from a verbal class ("fine to medium", "coarse to very coarse", "medium").

    Geometric mean over the span of the Wentworth classes named.  Assumption."""
    t = text.lower().replace("-", " ").replace(" to ", ",")
    names = sorted(WENTWORTH_MM, key=len, reverse=True)
    found = []
    for part in (p.strip() for p in t.split(",")):
        for n in names:
            if n in part:
                found.append(n)
                break
    if not found:
        raise ValueError(f"no Wentworth class in {text!r}")
    lo = min(WENTWORTH_MM[n][0] for n in found)
    hi = max(WENTWORTH_MM[n][1] for n in found)
    return 1e-3 * float(np.sqrt(lo * hi))


@dataclass
class UnitMineralogy:
    unit: str
    porosity: float
    minerals: list            # XRD class names with non-zero amount
    vf_bulk: np.ndarray        # m^3 mineral per m^3 bulk
    specific_area: np.ndarray  # m^2 per m^3 mineral (geometric x roughness)
    grain_d_m: float

    @property
    def reactive_area(self) -> np.ndarray:
        """m^2 per m^3 bulk, same definition as damkohler.reactive_area."""
        return self.vf_bulk * self.specific_area


def unit_mineralogy(unit: str, porosity: Optional[float] = None, grain_size_text: Optional[str] = None,
                    clay_d_m: float = 1.0e-6, roughness: float = 1.0,
                    density: Optional[Dict[str, float]] = None) -> UnitMineralogy:
    """Volume fractions and geometric specific areas for one Freiburg unit.

    Porosity and grain size default to the Table 3 samples of that unit
    (arithmetic-mean porosity; grain size from the described samples).
    """
    rho = dict(DENSITY_G_CM3, **(density or {}))
    wt = load_freiburg_table1()[unit]
    samples = [s for s in load_freiburg_table3() if s["unit"] == unit]
    if porosity is None:
        porosity = float(np.mean([s["porosity"] for s in samples]))
    if grain_size_text is None:
        texts = [s["grain_size_text"] for s in samples if s["grain_size_text"]]
        if not texts:
            raise ValueError(f"{unit}: no grain-size description in Freiburg et al. 2022; pass grain_size_text")
        d = float(np.exp(np.mean([np.log(grain_diameter_m(t)) for t in texts])))
    else:
        d = grain_diameter_m(grain_size_text)
    names = [m for m in NON_CLAY + CLAY if wt[m] > 0]
    v = np.array([wt[m] / rho[m] for m in names])
    vf_solid = v / v.sum()                       # Table 1 rows do not sum to exactly 100
    spec = np.array([6.0 / (clay_d_m if m in CLAY else d) for m in names]) * roughness
    return UnitMineralogy(unit, porosity, names, (1.0 - porosity) * vf_solid, spec, d)


def c_eq_scales(phases, T: float, P: float, nacl_molal: float, pco2_atm: float,
                database: str = "phreeqc.dat", water_density: float = 1000.0,
                floor: float = 1e-9) -> np.ndarray:
    """Characteristic concentration for the Damkohler number, mol per m^3 brine.

    For each phase separately: a NaCl brine at (T, P) is equilibrated with
    CO2(g) at ``pco2_atm`` (PHREEQC partial-pressure target) and with that phase
    alone; c_eq is |moles of phase dissolved or precipitated| per kg water,
    times the water density.  Needs ``pip install phreeqc``.
    """
    from .phreeqc_backend import _phreeqc
    out = []
    for ph in phases:
        p = _phreeqc(database)
        inp = f"""SELECTED_OUTPUT
 -reset false
USER_PUNCH
 -headings d
 10 PUNCH EQUI_DELTA("{ph}")
SOLUTION 1
 temp {T - 273.15:.4f}
 pressure {P / 101325.0:.4f}
 units mol/kgw
 pH 7 charge
 Na {nacl_molal}
 Cl {nacl_molal}
EQUILIBRIUM_PHASES 1
 CO2(g) {np.log10(pco2_atm):.6f} 100
 {ph} 0 10
END"""
        if p.RunString(inp):
            raise RuntimeError(f"{ph}: {p.GetErrorString()[:500]}")
        sel = p.GetSelectedOutput()
        out.append(max(abs(float(sel["d"][-1])) * water_density, floor))
    return np.array(out)
